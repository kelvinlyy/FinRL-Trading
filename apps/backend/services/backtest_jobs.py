from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = PROJECT_ROOT / "src/strategies/output/weights/adaptive_rotation"
JOBS_ROOT = PROJECT_ROOT / ".web_backtest_jobs"
META_NAME = "meta.json"
MAX_TAIL_CHARS = 14_000
MAX_JOBS_RETAINED = 40


def _infer_progress(stdout: str, stderr: str, status: str) -> dict[str, Any]:
    """Best-effort progress from ``deploy.sh`` step banners and strategy log lines."""
    text = f"{stdout or ''}\n{stderr or ''}"
    if status == "completed":
        return {"pct": 100, "label": "Finished", "phase": "done", "indeterminate": False}
    if status == "failed":
        return {"pct": 100, "label": "Failed", "phase": "failed", "indeterminate": False}
    if status == "queued":
        return {"pct": 3, "label": "Queued…", "phase": "queued", "indeterminate": True}

    if (
        "Enhanced chart saved to:" in text
        or "Backtest Summary" in text
        or "Detailed portfolio weights saved to:" in text
    ):
        return {"pct": 97, "label": "Saving outputs…", "phase": "finalize", "indeterminate": False}

    prog_matches = list(re.finditer(r"Progress:\s*(\d+)/(\d+)\s*days scanned", text))
    if prog_matches:
        last = prog_matches[-1]
        cur, total = int(last.group(1)), max(int(last.group(2)), 1)
        frac = min(cur / total, 1.0)
        pct = int(52 + frac * 44)
        return {
            "pct": min(max(pct, 52), 96),
            "label": f"Simulation: day {cur} / {total}",
            "phase": "strategy_loop",
            "indeterminate": False,
        }

    if "[3/3]" in text:
        if "2. Initializing strategy engine" in text:
            return {"pct": 56, "label": "Initializing strategy engine…", "phase": "strategy_init", "indeterminate": False}
        if "1. Loading and preprocessing data" in text:
            return {"pct": 50, "label": "Loading market data…", "phase": "strategy_load", "indeterminate": False}
        return {"pct": 47, "label": "Running strategy backtest…", "phase": "strategy_start", "indeterminate": False}

    if "[2/3]" in text:
        extracted = re.search(r"Extracted\s+(\d+)\s+symbols", text)
        total_sym = int(extracted.group(1)) if extracted else None
        ok_lines = re.findall(r"(?m)^\s*OK:\s*\S+", text)
        ok_count = len(ok_lines)
        if total_sym and total_sym > 0 and ok_count > 0:
            frac = min(ok_count / total_sym, 1.0)
            pct = int(24 + frac * 22)
            return {
                "pct": min(max(pct, 24), 45),
                "label": f"Downloading prices ({ok_count}/{total_sym} symbols)",
                "phase": "data_download",
                "indeterminate": False,
            }
        if "Skipping download" in text:
            return {"pct": 40, "label": "Using cached market data…", "phase": "data_skip", "indeterminate": False}
        return {"pct": 28, "label": "Preparing market data…", "phase": "data_prep", "indeterminate": False}

    if "[1/3]" in text:
        return {"pct": 14, "label": "Checking dependencies…", "phase": "deps", "indeterminate": False}

    if status == "running":
        return {"pct": 8, "label": "Starting pipeline…", "phase": "starting", "indeterminate": True}

    return {"pct": 5, "label": "Waiting…", "phase": "unknown", "indeterminate": True}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _truncate(text: str, limit: int = MAX_TAIL_CHARS) -> str:
    if len(text) <= limit:
        return text
    return f"... (truncated)\n{text[-limit:]}"


def _validate_iso_date(label: str, value: str) -> None:
    if not _DATE_RE.match(value):
        raise ValueError(f"{label} must be YYYY-MM-DD")
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"{label} is not a valid calendar date") from exc


def _atomic_write_meta(job_dir: Path, meta: dict) -> None:
    meta["updated_at"] = _utc_now()
    raw = json.dumps(meta, indent=2)
    tmp = job_dir / ".meta.tmp"
    out = job_dir / META_NAME
    job_dir.mkdir(parents=True, exist_ok=True)
    tmp.write_text(raw, encoding="utf-8")
    tmp.replace(out)


def _job_dir(job_id: str) -> Path:
    return JOBS_ROOT / job_id


def _read_log_tail(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text


@dataclass
class BacktestJob:
    job_id: str
    start: str
    end: str
    status: str = "queued"
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    error: str | None = None
    result_run_id: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "start": self.start,
            "end": self.end,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "returncode": self.returncode,
            "result_run_id": self.result_run_id,
            "message": self.error,
            "stdout_tail": _truncate(self.stdout) if self.stdout else None,
            "stderr_tail": _truncate(self.stderr) if self.stderr else None,
            "progress": _infer_progress(self.stdout, self.stderr, self.status),
        }


def _build_env() -> dict[str, str]:
    import os

    env = os.environ.copy()
    apps = str(PROJECT_ROOT / "apps")
    src = str(PROJECT_ROOT / "src")
    root = str(PROJECT_ROOT)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{apps}:{src}:{root}" + (f":{existing}" if existing else "")
    venv_bin = PROJECT_ROOT / ".venv" / "bin"
    if venv_bin.is_dir():
        env["PATH"] = f"{venv_bin}{os.pathsep}{env.get('PATH', '')}"
    return env


def _hydrate_from_disk(job_dir: Path) -> BacktestJob | None:
    meta_path = job_dir / META_NAME
    if not meta_path.is_file():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    stdout = _read_log_tail(job_dir / "deploy.stdout.log")
    stderr = _read_log_tail(job_dir / "deploy.stderr.log")

    return BacktestJob(
        job_id=meta["job_id"],
        start=meta["start"],
        end=meta["end"],
        status=meta.get("status", "unknown"),
        created_at=meta.get("created_at", _utc_now()),
        updated_at=meta.get("updated_at", _utc_now()),
        returncode=meta.get("returncode"),
        stdout=stdout,
        stderr=stderr,
        error=meta.get("error"),
        result_run_id=meta.get("result_run_id"),
    )


def get_job(job_id: str) -> BacktestJob | None:
    return _hydrate_from_disk(_job_dir(job_id))


def list_recent_jobs(limit: int = 25) -> list[dict[str, Any]]:
    if not JOBS_ROOT.is_dir():
        return []
    rows: list[tuple[str, dict[str, Any]]] = []
    for child in JOBS_ROOT.iterdir():
        if not child.is_dir():
            continue
        mp = child / META_NAME
        if not mp.is_file():
            continue
        try:
            meta = json.loads(mp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        key = meta.get("updated_at") or meta.get("created_at") or ""
        rows.append((key, meta))
    rows.sort(key=lambda x: x[0], reverse=True)
    out: list[dict[str, Any]] = []
    for _, meta in rows[:limit]:
        out.append(
            {
                "job_id": meta["job_id"],
                "status": meta.get("status"),
                "start": meta["start"],
                "end": meta["end"],
                "updated_at": meta.get("updated_at"),
                "result_run_id": meta.get("result_run_id"),
            }
        )
    return out


def _prune_old_jobs() -> None:
    if not JOBS_ROOT.is_dir():
        return
    dirs: list[tuple[str, Path]] = []
    for child in JOBS_ROOT.iterdir():
        if not child.is_dir():
            continue
        mp = child / META_NAME
        if not mp.is_file():
            continue
        try:
            meta = json.loads(mp.read_text(encoding="utf-8"))
            created = meta.get("created_at", "")
        except json.JSONDecodeError:
            created = ""
        dirs.append((created, child))
    if len(dirs) <= MAX_JOBS_RETAINED:
        return
    dirs.sort(key=lambda x: x[0])
    for _, path in dirs[: len(dirs) - MAX_JOBS_RETAINED]:
        shutil.rmtree(path, ignore_errors=True)


def spawn_job_worker(job_id: str) -> None:
    """Start ``backend.job_worker`` in a new session (survives normal API reload)."""
    job_dir = _job_dir(job_id)
    py = sys.executable
    subprocess.Popen(
        [py, "-m", "backend.job_worker", str(job_dir)],
        cwd=str(PROJECT_ROOT),
        env=_build_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def create_job(start: str, end: str) -> BacktestJob:
    _validate_iso_date("start", start)
    _validate_iso_date("end", end)
    if start >= end:
        raise ValueError("start must be before end")

    job_id = str(uuid.uuid4())
    job_dir = _job_dir(job_id)
    meta: dict[str, Any] = {
        "version": 1,
        "job_id": job_id,
        "start": start,
        "end": end,
        "status": "queued",
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "returncode": None,
        "result_run_id": None,
        "error": None,
    }
    _atomic_write_meta(job_dir, meta)
    _prune_old_jobs()
    spawn_job_worker(job_id)

    hydrated = get_job(job_id)
    if hydrated is None:
        raise RuntimeError("Failed to persist backtest job")
    return hydrated

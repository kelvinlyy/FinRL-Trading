"""
Detached process entrypoint: runs deploy.sh for one on-disk web backtest job.

Started via: python -m backend.job_worker <JOB_DIR>
(PYTHONPATH must include the repo ``apps`` directory.)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEPLOY_SCRIPT = PROJECT_ROOT / "deploy.sh"
META_NAME = "meta.json"


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _atomic_write_meta(job_dir: Path, meta: dict) -> None:
    meta["updated_at"] = _utc_now()
    raw = json.dumps(meta, indent=2)
    tmp = job_dir / ".meta.tmp"
    out = job_dir / META_NAME
    job_dir.mkdir(parents=True, exist_ok=True)
    tmp.write_text(raw, encoding="utf-8")
    tmp.replace(out)


def _build_env() -> dict[str, str]:
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


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python -m backend.job_worker JOB_DIR", file=sys.stderr)
        sys.exit(2)
    job_dir = Path(sys.argv[1]).resolve()
    meta_path = job_dir / META_NAME
    if not meta_path.is_file():
        print(f"meta missing: {meta_path}", file=sys.stderr)
        sys.exit(1)

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    job_id = meta.get("job_id", job_dir.name)
    start = meta["start"]
    end = meta["end"]
    strategy = meta.get("strategy", "adaptive_rotation")
    mode = meta.get("mode", "backtest")
    single_date = meta.get("single_date")
    dry_run = bool(meta.get("dry_run", False))
    account_name = meta.get("account_name")

    if not DEPLOY_SCRIPT.is_file():
        meta["status"] = "failed"
        meta["error"] = "deploy.sh not found at repository root"
        meta["returncode"] = None
        _atomic_write_meta(job_dir, meta)
        sys.exit(1)

    from backend.services.strategy_registry import resolve_strategy_output_dirs

    try:
        weights_dir, audit_dir = resolve_strategy_output_dirs(strategy)
    except (ValueError, FileNotFoundError) as exc:
        meta["status"] = "failed"
        meta["error"] = str(exc)
        meta["returncode"] = None
        _atomic_write_meta(job_dir, meta)
        sys.exit(1)

    meta["status"] = "running"
    meta["error"] = None
    meta["worker_pid"] = os.getpid()
    _atomic_write_meta(job_dir, meta)

    out_path = job_dir / "deploy.stdout.log"
    err_path = job_dir / "deploy.stderr.log"

    # Omit --skip-download so deploy.sh step [2/3] refreshes Yahoo CSVs under data/fmp_daily when needed.
    cmd = ["bash", str(DEPLOY_SCRIPT), "--strategy", strategy, "--mode", mode]
    if mode == "backtest":
        cmd += ["--start", start, "--end", end]
    elif mode == "single":
        cmd += ["--date", single_date or start]
    else:
        cmd += ["--date", single_date or start]
        if dry_run:
            cmd += ["--dry-run"]
        if account_name:
            cmd += ["--account", account_name]

    returncode: int | None = None
    try:
        with open(out_path, "w", encoding="utf-8", errors="replace") as out_f, open(
            err_path, "w", encoding="utf-8", errors="replace"
        ) as err_f:
            completed = subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT),
                env=_build_env(),
                stdout=out_f,
                stderr=err_f,
                timeout=3600,
            )
            returncode = completed.returncode
    except subprocess.TimeoutExpired:
        returncode = None
        meta["status"] = "failed"
        meta["error"] = "Job timed out after 60 minutes (large download or long backtest)"
        meta["returncode"] = None
        _atomic_write_meta(job_dir, meta)
        with open(err_path, "a", encoding="utf-8", errors="replace") as err_f:
            err_f.write("\n[job_worker: timeout]\n")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        meta["status"] = "failed"
        meta["error"] = str(exc)
        meta["returncode"] = None
        _atomic_write_meta(job_dir, meta)
        sys.exit(1)

    meta["returncode"] = returncode
    if mode == "backtest":
        run_id = f"{start}_to_{end}"
        # All registered runners write this summary file (adaptive, RSI, …).
        summary_csv = weights_dir / f"backtest_{start}_to_{end}.csv"
        if returncode == 0 and summary_csv.is_file():
            meta["status"] = "completed"
            meta["result_run_id"] = run_id
            meta["error"] = None
        elif returncode == 0:
            meta["status"] = "failed"
            meta["result_run_id"] = None
            meta["error"] = (
                f"deploy.sh exited 0 but expected summary CSV was not found ({summary_csv.name}). "
                "The strategy may have failed before saving outputs."
            )
        else:
            meta["status"] = "failed"
            meta["result_run_id"] = None
            meta["error"] = "Backtest command failed (non-zero exit)"
    elif mode == "single":
        d = single_date or start
        run_id = f"single_{d}"
        audit_json = audit_dir / f"audit_{d}.json"
        if returncode == 0 and audit_json.is_file():
            meta["status"] = "completed"
            meta["result_run_id"] = run_id
            meta["error"] = None
        elif returncode == 0:
            meta["status"] = "failed"
            meta["result_run_id"] = None
            meta["error"] = (
                f"deploy.sh exited 0 but expected audit file was not found ({audit_json.name}). "
                "Check deploy logs for strategy errors."
            )
        else:
            meta["status"] = "failed"
            meta["result_run_id"] = None
            meta["error"] = "Single-date deploy command failed (non-zero exit)"
    else:
        d = single_date or start
        run_id = f"paper_{d}"
        audit_json = weights_dir / f"execution_{d}.json"
        if returncode == 0 and audit_json.is_file():
            meta["status"] = "completed"
            meta["result_run_id"] = run_id
            meta["error"] = None
        elif returncode == 0:
            meta["status"] = "failed"
            meta["result_run_id"] = None
            meta["error"] = (
                f"deploy.sh exited 0 but expected execution log was not found ({audit_json.name}). "
                "Check deploy logs for trading errors."
            )
        else:
            meta["status"] = "failed"
            meta["result_run_id"] = None
            meta["error"] = "Paper deploy command failed (non-zero exit)"

    _atomic_write_meta(job_dir, meta)
    sys.exit(0 if meta["status"] == "completed" else 1)


if __name__ == "__main__":
    main()

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator

from backend.services.adaptive_yaml import KNOWN_GROUP_IDS, load_adaptive_rotation_public, save_adaptive_rotation_public

router = APIRouter(prefix="/api/config", tags=["config"])


def _secret_configured(value: object) -> bool:
    if value is None:
        return False
    getter = getattr(value, "get_secret_value", None)
    if callable(getter):
        try:
            return bool(getter())
        except Exception:
            return False
    s = str(value).strip()
    return bool(s)


@router.get("/runtime")
def runtime_public_config():
    """Non-secret runtime metadata (paths, booleans for optional credentials)."""
    try:
        from src.config.settings import get_config

        cfg = get_config()
        root = Path(__file__).resolve().parents[3]

        def _abs(p: str | Path) -> str:
            q = Path(p)
            out = q if q.is_absolute() else (root / q)
            try:
                return str(out.resolve())
            except OSError:
                return str(out)

        return {
            "app_name": cfg.app_name,
            "version": cfg.version,
            "environment": cfg.environment,
            "paths": {
                "repo_root": str(root),
                "data_base_dir": _abs(cfg.data.base_dir),
                "data_cache_dir": _abs(cfg.data.cache_dir),
                "data_processed_dir": _abs(cfg.data.processed_dir),
                "database_path": _abs(cfg.get_database_path()),
            },
            "credentials_configured": {
                "alpaca_api_key": bool(cfg.alpaca.api_key and str(cfg.alpaca.api_key).strip()),
                "alpaca_api_secret": bool(cfg.alpaca.api_secret and str(cfg.alpaca.api_secret).strip()),
                "fmp_api_key": _secret_configured(cfg.fmp.api_key),
                "openai_api_key": _secret_configured(cfg.openai.api_key),
                "wrds_username": bool(cfg.wrds.username and str(cfg.wrds.username).strip()),
            },
            "alpaca": {
                "base_url": cfg.alpaca.base_url,
                "use_paper_trading": cfg.alpaca.use_paper_trading,
            },
            "web_legacy_streamlit_port": cfg.web.port,
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Could not load settings: {exc}") from exc


class _GroupWrite(BaseModel):
    id: str
    max_assets: int = Field(ge=1, le=20)
    symbols: list[str] = Field(min_length=1)

    @field_validator("symbols", mode="after")
    @classmethod
    def strip_nonempty(cls, v: list[str]) -> list[str]:
        out = [str(s).strip() for s in v if str(s).strip()]
        if not out:
            raise ValueError("Each group needs at least one non-empty symbol.")
        return out


class _FallbackWrite(BaseModel):
    enabled: bool
    symbols: list[str] = Field(min_length=1)

    @field_validator("symbols", mode="after")
    @classmethod
    def strip_nonempty_fb(cls, v: list[str]) -> list[str]:
        out = [str(s).strip() for s in v if str(s).strip()]
        if not out:
            raise ValueError("Fallback needs at least one non-empty symbol.")
        return out


class AdaptiveRotationWriteBody(BaseModel):
    """Equal-weight excess benchmark: one or more tickers (same return math as a rotation group)."""

    excess_return_benchmark_symbols: list[str] = Field(min_length=1, max_length=20)

    @field_validator("excess_return_benchmark_symbols", mode="after")
    @classmethod
    def strip_nonempty_bench(cls, v: list[str]) -> list[str]:
        out = [str(s).strip() for s in v if str(s).strip()]
        if not out:
            raise ValueError("Benchmark group needs at least one non-empty symbol.")
        return out

    portfolio_fallback: _FallbackWrite
    asset_groups: list[_GroupWrite]

    @model_validator(mode="after")
    def ids_complete(self) -> AdaptiveRotationWriteBody:
        got = {g.id for g in self.asset_groups}
        if got != set(KNOWN_GROUP_IDS):
            raise ValueError(f"asset_groups ids must be exactly: {list(KNOWN_GROUP_IDS)}")
        return self


@router.get("/adaptive-rotation")
def adaptive_rotation_config():
    """Return rotation groups, fallback sleeve, benchmark, and which baseline CSVs exist on disk."""
    try:
        return load_adaptive_rotation_public()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/adaptive-rotation")
def adaptive_rotation_put(body: AdaptiveRotationWriteBody):
    """Rewrite universe sections in ``AdaptiveRotationConf_v1.2.1.yaml`` (full-file YAML dump)."""
    try:
        return save_adaptive_rotation_public(body.model_dump(mode="json"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

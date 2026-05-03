from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator

from backend.services.adaptive_yaml import KNOWN_GROUP_IDS, load_adaptive_rotation_public, save_adaptive_rotation_public

router = APIRouter(prefix="/api/config", tags=["config"])


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

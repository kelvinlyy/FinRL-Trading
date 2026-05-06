"""Read-only trading readiness endpoints for the apps console."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.services.trading_status import trading_status_public

router = APIRouter(prefix="/api/trading", tags=["trading"])


@router.get("/status")
def trading_status():
    try:
        return trading_status_public()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Could not load trading status: {exc}") from exc

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.services.portfolio import portfolio_overview

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/overview")
def get_portfolio_overview():
    try:
        return portfolio_overview()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Could not build portfolio overview: {exc}") from exc

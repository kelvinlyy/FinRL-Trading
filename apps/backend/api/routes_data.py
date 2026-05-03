"""Read-only data layer endpoints (local CSVs + DataStore stats)."""

from __future__ import annotations

from fastapi import APIRouter

from backend.services.console_data import build_data_overview

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/overview")
def data_overview():
    """FMP daily folder scan, DataStore storage summary, and manual download guidance."""
    return build_data_overview()

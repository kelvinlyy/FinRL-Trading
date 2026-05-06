"""Read-only trading readiness endpoints for the apps console."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.backtest_jobs import create_job, get_job, list_recent_jobs
from backend.services.data_coverage import check_single_date_data_coverage
from backend.services.strategy_registry import config_path_for_strategy
from backend.services.trading_status import trading_status_public

router = APIRouter(prefix="/api/trading", tags=["trading"])


@router.get("/status")
def trading_status():
    try:
        return trading_status_public()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Could not load trading status: {exc}") from exc


class TradingRunRequest(BaseModel):
    strategy: str = Field("adaptive_rotation", description="Strategy name from deploy.sh STRATEGIES")
    date: str | None = Field(None, description="Decision date YYYY-MM-DD; defaults to today when omitted")
    dry_run: bool = Field(True, description="Preview orders only, do not submit broker orders")
    account_name: str | None = Field(None, description="Optional Alpaca account alias from environment config")


@router.post("/run")
def start_trading_run(body: TradingRunRequest):
    try:
        cfg_path = config_path_for_strategy(body.strategy)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    decision_date = (body.date or "").strip() or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        report = check_single_date_data_coverage(decision_date, config_path=cfg_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not report.ok:
        raise HTTPException(status_code=400, detail=report.to_detail_dict())
    try:
        job = create_job(
            start=decision_date,
            end=decision_date,
            strategy=body.strategy,
            mode="paper",
            single_date=decision_date,
            dry_run=body.dry_run,
            account_name=body.account_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job_id": job.job_id, "status": job.status}


@router.get("/jobs")
def trading_jobs_index():
    jobs = [j for j in list_recent_jobs() if j.get("mode") == "paper"]
    return {"jobs": jobs}


@router.get("/jobs/{job_id}")
def trading_job_status(job_id: str):
    job = get_job(job_id)
    if job is None or job.mode != "paper":
        raise HTTPException(status_code=404, detail="Trading job not found")
    return job.to_public_dict()

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from backend.services.backtest_jobs import allowed_modes_public, create_job, get_job, list_recent_jobs
from backend.services.strategy_registry import list_deploy_strategies

router = APIRouter(prefix="/api/backtest", tags=["backtest"])

BacktestMode = Literal["backtest", "single"]


class BacktestRunRequest(BaseModel):
    """Run a deploy.sh-backed job. Omit ``strategy`` / ``mode`` for legacy backtest-only clients."""

    start: str | None = Field(None, description="Backtest start date (YYYY-MM-DD); required when mode=backtest")
    end: str | None = Field(None, description="Backtest end date (YYYY-MM-DD); required when mode=backtest")
    date: str | None = Field(None, description="Decision date for mode=single (YYYY-MM-DD)")
    strategy: str = Field("adaptive_rotation", description="Strategy name from deploy.sh STRATEGIES")
    mode: BacktestMode = Field("backtest", description="backtest (range) or single (signal for one day)")

    @model_validator(mode="after")
    def validate_dates_for_mode(self):
        if self.mode == "backtest":
            if not self.start or not self.end:
                raise ValueError("mode=backtest requires start and end")
        elif self.mode == "single":
            if not self.date:
                raise ValueError("mode=single requires date")
        return self


@router.get("/strategies")
def backtest_strategies():
    """Strategies parsed from ``deploy.sh`` (UC1/UC2: add rows there to expose new runners)."""
    return {"strategies": list_deploy_strategies()}


@router.get("/modes")
def backtest_modes():
    return {"modes": allowed_modes_public()}


@router.post("/run")
def start_backtest(body: BacktestRunRequest):
    try:
        job = create_job(
            body.start or "",
            body.end or "",
            strategy=body.strategy,
            mode=body.mode,
            single_date=body.date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"job_id": job.job_id, "status": job.status}


@router.get("/jobs")
def backtest_jobs_index():
    return {"jobs": list_recent_jobs()}


@router.get("/jobs/{job_id}")
def backtest_job_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_public_dict()

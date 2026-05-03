from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.backtest_jobs import create_job, get_job, list_recent_jobs
from backend.services.data_coverage import check_backtest_data_coverage

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


class BacktestRunRequest(BaseModel):
    start: str = Field(..., description="Backtest start date (YYYY-MM-DD)")
    end: str = Field(..., description="Backtest end date (YYYY-MM-DD)")


@router.post("/run")
def start_backtest(body: BacktestRunRequest):
    try:
        report = check_backtest_data_coverage(body.start, body.end)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Server is missing a dependency needed for data checks: {exc}",
        ) from exc

    if not report.ok:
        raise HTTPException(status_code=400, detail=report.to_detail_dict())

    try:
        job = create_job(body.start, body.end)
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

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.services.results import (
    get_run,
    list_runs,
    read_summary,
    read_trade_log,
    read_weights,
    run_metadata,
)

router = APIRouter(prefix="/api/results", tags=["results"])


@router.get("")
def results_index():
    return {"results": [run_metadata(run) for run in list_runs()]}


@router.get("/{run_id}")
def result_detail(run_id: str):
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return run_metadata(run)


@router.get("/{run_id}/summary")
def result_summary(run_id: str):
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return {"rows": read_summary(run)}


@router.get("/{run_id}/trade-log")
def result_trades(run_id: str):
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return {"rows": read_trade_log(run)}


@router.get("/{run_id}/weights")
def result_weights(run_id: str):
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return {"rows": read_weights(run)}


@router.get("/{run_id}/chart")
def result_chart(run_id: str):
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Chart not found")

    path = run.chart_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Chart file missing")

    return FileResponse(path, media_type="image/png", filename=path.name)

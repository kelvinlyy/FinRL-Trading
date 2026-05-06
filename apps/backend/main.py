from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes_backtest import router as backtest_router
from backend.api.routes_config import router as config_router
from backend.api.routes_data import router as data_router
from backend.api.routes_portfolio import router as portfolio_router
from backend.api.routes_results import router as results_router
from backend.api.routes_trading import router as trading_router

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ARTIFACTS_DIR = _REPO_ROOT / "src/strategies/output/weights/adaptive_rotation"
_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


app = FastAPI(
    title="FinRL-X Console API",
    description="Console API: results, backtest jobs, adaptive config, data overview, runtime metadata.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(results_router)
app.include_router(backtest_router)
app.include_router(config_router)
app.include_router(data_router)
app.include_router(portfolio_router)
app.include_router(trading_router)
app.mount("/artifacts", StaticFiles(directory=str(_ARTIFACTS_DIR)), name="artifacts")


@app.get("/health")
def health():
    return {"status": "ok"}

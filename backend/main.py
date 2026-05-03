from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes_results import router as results_router


app = FastAPI(
    title="FinRL-X Console API",
    description="Read-only API for Adaptive Rotation backtest artifacts.",
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
app.mount("/artifacts", StaticFiles(directory="src/strategies/output/weights/adaptive_rotation"), name="artifacts")


@app.get("/health")
def health():
    return {"status": "ok"}

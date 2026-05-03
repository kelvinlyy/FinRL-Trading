# FinRL-X Backend

FastAPI service that exposes **read-only** Adaptive Rotation backtest artifacts produced by the Python strategy pipeline (`deploy.sh`, `run_adaptive_rotation_strategy.py`). The Next.js frontend consumes this API; it does not execute strategies itself.

---

## Design principles

- **Artifact-centric:** Runs are discovered from files under `src/strategies/output/weights/adaptive_rotation/` (PNG charts, CSVs). No database for results.
- **Thin HTTP layer:** Routing lives in `backend/api/`; parsing and domain logic live in `backend/services/`.
- **CORS for local dev:** Allows `localhost:3000` / `127.0.0.1:3000` for the static Next.js app (see `backend/main.py`).
- **Optional static hosting:** Generated PNGs are also served under `/artifacts/…` for direct links.

---

## Architecture

```
backend/
├── main.py                 # FastAPI app, CORS, mounts results router + /artifacts static
├── api/
│   └── routes_results.py   # REST routes under /api/results
└── services/
    └── results.py          # Run discovery, CSV reads, equity / visualization payloads
```

**Data flow**

1. Strategy run writes `enhanced_backtest_{start}_to_{end}.png`, `ars_portfolio_weights_*.csv`, `backtest_*.csv`, `trade_log_*.csv`, etc.
2. `list_runs()` scans PNG filenames to build stable `run_id` values (`{start}_to_{end}`).
3. Clients request metadata, tabular data, static chart bytes, or **`/{run_id}/visualization`** — a JSON bundle for the interactive chart (equity curve, drawdown, regimes, group timeline, trades, `initial_capital`).

**Dependencies:** Python 3.11+, FastAPI, Uvicorn, Pandas. Price CSVs for benchmarks live under `data/fmp_daily/` when computing equity multipliers in visualization.

---

## Functionality

| Area | Description |
|------|-------------|
| **Run catalog** | Lists saved runs with labels, date range, artifact URLs, row counts. |
| **Run metadata** | Single-run summary: links to chart, trade log, summary, weights, visualization JSON. |
| **Summary CSV** | Weekly / periodic metrics from `backtest_*.csv`. |
| **Trade log** | Rows from `trade_log_*.csv`. |
| **Weights** | Raw portfolio weights CSV for inspection. |
| **Chart PNG** | Serves the matplotlib-generated `enhanced_backtest_*.png`. |
| **Visualization JSON** | Structured series for the SPA: equity (strategy + SPY/QQQ), drawdown, regime bands, group activation timeline, trades; includes `initial_capital` (default notionals scale). Group lanes show at most **two** activated groups per date (top two by total group weight), matching `max_active_groups` in the Adaptive Rotation config. |

**Out of scope (by design):** live trading, auth, persisting user settings, triggering backtests over HTTP, non–Adaptive-Rotation strategies.

---

## How to start

### Prerequisites

- Python **3.11+**
- Repository root on `PYTHONPATH` so `backend` and `src` resolve (`PYTHONPATH=/path/to/repo:/path/to/repo/src`).
- Optional: Adaptive Rotation artifacts already generated under `src/strategies/output/weights/adaptive_rotation/` (otherwise `/api/results` may return an empty list).

### Install

From the **repository root**:

```bash
pip install -r requirements.txt
# If needed (known PyPI name mismatch):
pip install finnhub-python pyyaml fastapi uvicorn
```

### Run the API (development)

```bash
cd /path/to/repo
PYTHONPATH=/path/to/repo:/path/to/repo/src \
  python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Docs / OpenAPI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health:** `GET /health` → `{"status":"ok"}`

### Environment

No mandatory env vars for read-only results. Optional keys (Alpaca, FMP, etc.) are for the broader FinRL-X stack, not required for this API alone.

---

## API reference

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness check |
| `GET` | `/api/results` | List runs (`{ "results": [...] }`) |
| `GET` | `/api/results/{run_id}` | Run metadata + artifact URLs |
| `GET` | `/api/results/{run_id}/summary` | `{ "rows": [...] }` from summary CSV |
| `GET` | `/api/results/{run_id}/trade-log` | `{ "rows": [...] }` |
| `GET` | `/api/results/{run_id}/weights` | `{ "rows": [...] }` |
| `GET` | `/api/results/{run_id}/visualization` | JSON for interactive dashboard chart |
| `GET` | `/api/results/{run_id}/chart` | PNG file response |
| `GET` | `/artifacts/{filename}` | Static files from the adaptive_rotation output dir |

`run_id` matches the pattern `{YYYY-MM-DD}_to_{YYYY-MM-DD}` derived from `enhanced_backtest_*_to_*.png` filenames.

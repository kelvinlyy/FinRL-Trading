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
apps/backend/
├── main.py                 # FastAPI app, CORS, mounts results router + /artifacts static
├── api/
│   ├── routes_results.py   # REST routes under /api/results
│   ├── routes_backtest.py  # Job launch + polling
│   ├── routes_data.py      # Data layer overview
│   ├── routes_config.py    # Runtime + adaptive YAML endpoints
│   └── routes_trading.py   # Read-only trading readiness
└── services/
    └── results.py          # Run discovery, CSV reads, equity / visualization payloads
```

**Data flow**

1. Strategy run writes `enhanced_backtest_{start}_to_{end}.png`, `ars_portfolio_weights_*.csv`, `backtest_*.csv`, `trade_log_*.csv`, etc.
2. `list_runs()` scans PNG filenames to build stable `run_id` values (`{start}_to_{end}`).
3. Clients request metadata, tabular data, static chart bytes, or `**/{run_id}/visualization`** — a JSON bundle for the interactive chart (equity curve, drawdown, regimes, group timeline, trades, `initial_capital`).

**Dependencies:** Python 3.11+, FastAPI, Uvicorn, Pandas. Price CSVs for benchmarks live under `data/fmp_daily/` when computing equity multipliers in visualization.

---

## Functionality


| Area                   | Description                                                                                                                                                                                                                                                                                                                            |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Run catalog**        | Lists saved runs with labels, date range, artifact URLs, row counts.                                                                                                                                                                                                                                                                   |
| **Run metadata**       | Single-run summary: links to chart, trade log, summary, weights, visualization JSON.                                                                                                                                                                                                                                                   |
| **Summary CSV**        | Weekly / periodic metrics from `backtest_*.csv`.                                                                                                                                                                                                                                                                                       |
| **Trade log**          | Rows from `trade_log_*.csv`.                                                                                                                                                                                                                                                                                                           |
| **Weights**            | Raw portfolio weights CSV for inspection.                                                                                                                                                                                                                                                                                              |
| **Chart PNG**          | Serves the matplotlib-generated `enhanced_backtest_*.png`.                                                                                                                                                                                                                                                                             |
| **Visualization JSON** | Structured series for the SPA: equity (strategy + SPY/QQQ), drawdown, regime bands, group activation timeline, trades; includes `initial_capital`, `max_timeline_active_groups` (2), and per-row `group_weight_total` for each of the three display groups. The chart keeps at most **two** lanes per date (ranked by total group weight); the frontend applies the same cap again as a safeguard. |
| **Data overview**      | CSV cache and SQLite stats for the data layer (`/api/data/overview`). |
| **Runtime config**     | Non-secret settings and credential booleans (`/api/config/runtime`) plus adaptive rotation YAML read/write (`/api/config/adaptive-rotation`). |
| **Trading status**     | Read-only paper/live readiness metadata (`/api/trading/status`); no broker order execution from HTTP. |


**Out of scope (by design):** broker order execution over HTTP, auth, persisting user settings, non–Adaptive-Rotation strategy execution logic.

---

## How to start

### Prerequisites

- Python **3.11+**
- Repository **`apps/`** directory on `PYTHONPATH` so the `backend` package and `src` resolve (`PYTHONPATH=/path/to/repo/apps:/path/to/repo:/path/to/repo/src`).
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
PYTHONPATH=/path/to/repo/apps:/path/to/repo:/path/to/repo/src \
  python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Docs / OpenAPI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health:** `GET /health` → `{"status":"ok"}`

### Environment

No mandatory env vars for read-only results. Optional keys (Alpaca, FMP, etc.) are for the broader FinRL-X stack, not required for this API alone.

---

## API reference


| Method | Path                                  | Purpose                                            |
| ------ | ------------------------------------- | -------------------------------------------------- |
| `GET`  | `/health`                             | Liveness check                                     |
| `GET`  | `/api/results`                        | List runs (`{ "results": [...] }`)                 |
| `GET`  | `/api/results/{run_id}`               | Run metadata + artifact URLs                       |
| `GET`  | `/api/results/{run_id}/summary`       | `{ "rows": [...] }` from summary CSV               |
| `GET`  | `/api/results/{run_id}/trade-log`     | `{ "rows": [...] }`                                |
| `GET`  | `/api/results/{run_id}/weights`       | `{ "rows": [...] }`                                |
| `GET`  | `/api/results/{run_id}/visualization` | JSON for interactive dashboard chart               |
| `GET`  | `/api/results/{run_id}/chart`         | PNG file response                                  |
| `GET`  | `/artifacts/{filename}`               | Static files from the adaptive_rotation output dir |
| `GET`  | `/api/data/overview`                  | Local CSV + SQLite summary                         |
| `GET`  | `/api/config/runtime`                 | Non-secret runtime metadata                        |
| `GET`  | `/api/config/adaptive-rotation`       | Read adaptive YAML public fields                   |
| `PUT`  | `/api/config/adaptive-rotation`       | Save adaptive YAML universe fields                 |
| `GET`  | `/api/backtest/strategies`            | Strategies parsed from `deploy.sh`                 |
| `POST` | `/api/backtest/run`                   | Queue deploy-backed backtest/single job            |
| `GET`  | `/api/backtest/jobs`                  | List recent jobs                                   |
| `GET`  | `/api/backtest/jobs/{job_id}`         | Poll job status                                    |
| `GET`  | `/api/trading/status`                 | Deferred live/paper trading status                 |


`run_id` matches the pattern `{YYYY-MM-DD}_to_{YYYY-MM-DD}` derived from `enhanced_backtest_*_to_*.png` filenames.
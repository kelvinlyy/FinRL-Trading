# AGENTS.md

## Cursor Cloud specific instructions

### Overview

FinRL-X is a Python-based quantitative trading platform. The core development workflow involves backtesting strategies, running the Streamlit dashboard, and (optionally) paper trading via Alpaca.

### Mandatory: restart dev servers after code changes

Whenever you **edit** `backend/`, `frontend/`, `scripts/restart-dev-stack.sh`, or anything that affects the running API or Next app, you **must** before finishing the turn:

1. Run **`./scripts/restart-dev-stack.sh`** from the repo root (use **`--clean-next`** if the user reported Next 500 / missing chunk errors).
2. Confirm smoke checks pass (`GET /docs` and `GET /` return 200 in script output); if not, fix and retry.
3. Tell the user to **hard-refresh** the browser on `http://localhost:3000` — you cannot refresh their tab for them.

Skipping this step is not acceptable; the user should not have to ask for a restart separately.

### Mandatory: verify before responding (quality gate)

Before telling the user that backend or frontend work is **done**, run checks so unrelated areas are less likely to break:

| Change touched | Run before responding |
|----------------|----------------------|
| **`frontend/`** | `./scripts/verify-frontend.sh` (runs **`npm run clean`** then **`npm run build`** to avoid stale `.next` flakes). |
| **`backend/`** | `python3 -m py_compile` on edited `.py` files, or `pytest` / smoke **`curl http://127.0.0.1:8000/docs`** after **`restart-dev-stack.sh`**. |
| **Both** | Both rows above. |

Do **not** claim the UI “should work” without at least **frontend build success** when TS/React changed. Fix failures before ending the turn.

### Environment

- **Python 3.11+** is required (`python_requires=">=3.11"` in `setup.py`).
- Set `PYTHONPATH=/workspace/src:/workspace` before running any Python commands (CLI, Streamlit, strategy runners).
- Copy `.env.example` to `.env` if it doesn't exist. The `.env` file is required for configuration; default values work for backtesting (no API keys needed).
- The `requirements.txt` lists `finnhub>=2.4.19` but the correct PyPI package is `finnhub-python`. Install it separately: `pip install finnhub-python`.

### Next.js + FastAPI stack (command center)

This section expands on **Mandatory: restart dev servers** above. Same rule: **always** restart after relevant edits using the script below.

**One-shot restart** (from repo root):

```bash
./scripts/restart-dev-stack.sh
```

If the frontend serves stale chunks or 500s (`Cannot find module './NNN.js'`):

```bash
./scripts/restart-dev-stack.sh --clean-next
```

**Manual equivalents:** kill ports **8000** (uvicorn) and **3000** (next); start backend with `PYTHONPATH=/workspace:/workspace/src python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload`; start frontend with `cd frontend && npm run dev`.

Agents cannot click “refresh” in the user’s browser; after restart, **tell the user to hard-refresh** `http://localhost:3000` (and `/results`).

### Key commands


| Task                | Command                                                                                        |
| ------------------- | ---------------------------------------------------------------------------------------------- |
| **Restart API + Next** | `./scripts/restart-dev-stack.sh` (after backend/frontend changes; `--clean-next` if Next is broken) |
| **Verify frontend** | `./scripts/verify-frontend.sh` (required before saying frontend work is complete) |
| Install deps        | `pip install -r requirements.txt` (skip finnhub line) then `pip install finnhub-python pyyaml` |
| Backtest            | `./deploy.sh --strategy adaptive_rotation --mode backtest --start 2024-01-01 --end 2024-12-31` |
| Single signal       | `./deploy.sh --strategy adaptive_rotation --mode single --date 2024-12-31`                     |
| Streamlit dashboard | `streamlit run src/web/app.py --server.port 8501 --server.headless true`                       |
| CLI config          | `python src/main.py config`                                                                    |
| Lint (black)        | `black --check src/`                                                                           |
| Lint (flake8)       | `flake8 src/ --max-line-length=120`                                                            |
| Type check          | `mypy src/`                                                                                    |
| Tests               | `pytest` (no test files exist yet; framework is configured)                                    |


### Gotchas

- The repo is missing `src/utils/logging_utils.py` which is imported by `src/main.py` and `src/web/app.py`. A minimal implementation providing `setup_logging()` is needed for the CLI and dashboard to work.
- The first backtest run downloads market data via Yahoo Finance into `data/fmp_daily/`. Subsequent runs can use `--skip-download` to skip the download step.
- `deploy.sh` handles data download, dependency checks, and strategy execution in one command. It's the recommended entry point for backtesting.
- No external services (Postgres, Redis, Docker) are needed for development. SQLite is the default embedded database.
- Alpaca API keys are only required for paper/live trading mode, not for backtesting.
- The Streamlit dashboard runs on port 8501 by default.
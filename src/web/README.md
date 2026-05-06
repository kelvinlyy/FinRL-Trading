# Legacy Streamlit Dashboard

`src/web/app.py` is now a **legacy notice page**.
`src/web/components.py` is also intentionally deprecated and raises an explicit error if imported.

All active web feature development has migrated to:

- `apps/frontend` (Next.js, `http://localhost:3000`)
- `apps/backend` (FastAPI, `http://127.0.0.1:8000/docs`)

## Recommended local workflow

From repository root:

```bash
./scripts/restart-dev-stack.sh
```

Then hard-refresh `http://localhost:3000`.

## Strategy execution

For non-UI runs, continue using `deploy.sh`:

```bash
./deploy.sh --strategy adaptive_rotation --mode backtest
```

For paper-trading execution:

```bash
./deploy.sh --strategy adaptive_rotation --mode paper --dry-run
```

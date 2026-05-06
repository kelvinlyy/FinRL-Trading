# FinRL Trading Console (Frontend)

**Next.js 15** (App Router) + **Tailwind CSS 3** single-page experience for FinRL-X Adaptive Rotation results. UI language follows the **Mercury – Mountain Top Command Center** direction (Refero): dark surfaces, restrained typography, Mercury Blue accents, “command” layout.

The app is **static-first**: pages are mostly server components that fetch the FastAPI backend at request time. Legacy Streamlit-only surfaces are either migrated (`/data`, `/settings`) or explicitly deferred with in-app notices (`/portfolio`, `/trading`).

---

## Design system


| Token / pattern | Role                                                                                                                                                                 |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Colors**      | `mercury-blue` (#5266eb) primary actions; `deep-space` / `midnight-slate` backgrounds; `starlight` / `silver` text; `lead` borders (see `tailwind.config.ts`).       |
| **Typography**  | Inter / Manrope stack; scale from `caption` through `display` for hierarchy.                                                                                         |
| **Surfaces**    | `.panel` — bordered, blurred panels on a radial + linear gradient body (`app/globals.css`).                                                                          |
| **Shape**       | Pill CTAs (`rounded-[32px]`), generous spacing, max content width `1200px`.                                                                                          |
| **Charts**      | SVG-based interactive report (`components/interactive-backtest-chart.tsx`): strategy / SPY / QQQ colors aligned with legend; regime shading; group activation lanes. |


Reference mood: [Mercury style – Refero](https://styles.refero.design/) (dark operational dashboard, not a marketing landing page).

---

## Architecture

```
apps/frontend/
├── app/                      # Next.js App Router
│   ├── layout.tsx            # Root layout, fonts, globals
│   ├── page.tsx              # Command / home
│   ├── results/page.tsx      # Saved runs + interactive chart
│   ├── data/page.tsx         # Data overview (CSV + SQLite stats)
│   ├── settings/page.tsx     # Runtime metadata + credential booleans
│   ├── portfolio/page.tsx    # Portfolio-analysis migration notice
│   └── trading/page.tsx      # Live/paper-trading readiness notice
├── components/               # UI building blocks + chart
├── lib/
│   ├── api.ts                # fetch() helpers → FastAPI
│   └── types.ts              # TypeScript models aligned with backend JSON
├── app/globals.css           # Base styles + panel utilities
├── tailwind.config.ts        # Mercury tokens
└── package.json
```

**Data flow**

1. Server components call `getRuns()`, `getRun()`, `getVisualization()` in `lib/api.ts`.
2. `NEXT_PUBLIC_API_BASE_URL` (default `http://127.0.0.1:8000`) must point at the FastAPI instance.
3. `InteractiveBacktestChart` is a client component; it receives **visualization** JSON and renders SVG (equity, drawdown, regimes, group timeline, hover snapshot).

**Build output:** `next build` produces a production bundle; `next start` serves it. Development uses `next dev`.

---

## Functionality


| Route / area    | What it does                                                                                                                                            |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `**/`**         | Command dashboard: universe config + backtest launch with navigation to all app surfaces.                                                              |
| `**/results`**  | Lists discovered runs (from API); run selector; summary cards; **interactive** equity / regime / drawdown / group-timeline chart; link to download PNG. |
| `**/data`**     | Read-only data layer status (CSV cache + SQLite record stats + refresh guidance).                                                                       |
| `**/settings`** | Runtime metadata and non-secret credential readiness flags.                                                                                              |
| `**/portfolio`** | Explicit deferred notice: dedicated account-level portfolio analytics are not in the app yet; use `/results` for run analytics.                         |
| `**/trading`**  | Explicit deferred notice: live/paper broker execution is CLI-only; page shows readiness status from backend.                                            |


**Not included:** broker order execution from web requests, settings persistence, generic demo backtests.

---

## How to start

### Prerequisites

- **Node.js 18+** (Next 15.x compatible with the version pinned in `package.json`).
- Backend running (see `apps/backend/README.md`) if you want real runs and charts; otherwise the API client may fall back to empty or minimal data depending on `lib/api.ts` behavior.

### Install

```bash
cd apps/frontend
npm install
```

### Development

```bash
npm run dev
```

Opens **[http://localhost:3000](http://localhost:3000)** (see `package.json` — dev server binds `0.0.0.0:3000`).

Point the browser at the API:

```bash
# Same shell as npm run dev, or use .env.local:
echo 'NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000' > .env.local
```

Adjust host/port if Uvicorn listens elsewhere.

### Production build

```bash
npm run build
npm run start
```

### Lint

```bash
npm run lint
```

---

## Troubleshooting


| Issue                                     | Hint                                                                                                                                                          |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **500** / `Cannot find module './NNN.js'` | Stale `.next` build output. Run **`npm run clean`**, then **`npm run build`**, and restart the dev or production server. Or delete `apps/frontend/.next` manually. |
| Group timeline: **three lanes** at **start** or **end** | Avoid stretching segment dates to the chart edges (fixed in `interactive-backtest-chart.tsx`). Bars begin where each group first has holdings after the max-2 cap. Restart after pull; hard-refresh. |
| Empty results list                        | Run Adaptive Rotation backtest so artifacts exist under `src/strategies/output/weights/adaptive_rotation/`, or check backend logs.                            |
| Chart missing / failed fetch              | Confirm `GET /api/results/{id}/visualization` returns 200; CORS and `NEXT_PUBLIC_API_BASE_URL` must match how you open the site (`localhost` vs `127.0.0.1`). |
| Type errors after pulling                 | Run `npm install` and `npm run build`.                                                                                                                        |



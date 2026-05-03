# FinRL Trading Frontend

Static Next.js + Tailwind interface inspired by the Mercury Refero style:
dark command-center surfaces, spacious layout, restrained typography, and a
single Mercury Blue CTA accent.

## Scope

This frontend intentionally includes only real/static content:

- Command dashboard
- Saved Adaptive Rotation results
- Strategy anatomy / methodology

It does **not** include the former Streamlit app's TBD sections such as live
trading controls, settings persistence, generic demo backtests, or mock
portfolio analytics.

## Run

```bash
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_BASE_URL` if the backend is not running on
`http://localhost:8000`.

## Build

```bash
npm run build
```


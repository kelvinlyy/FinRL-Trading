"""
Legacy Streamlit entrypoint.

FinRL-X web migration is now centered on:
- apps/frontend (Next.js, port 3000)
- apps/backend (FastAPI, port 8000)
"""

from __future__ import annotations

import streamlit as st


def main() -> None:
    st.set_page_config(
        page_title="FinRL-X Legacy Streamlit",
        page_icon="⚠️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.title("FinRL-X Streamlit is deprecated")
    st.warning(
        "All active web features have migrated to the apps stack "
        "(Next.js + FastAPI)."
    )

    st.markdown(
        """
### Use these endpoints instead

- **Console UI**: http://localhost:3000
- **API docs**: http://127.0.0.1:8000/docs

### Local startup

```bash
./scripts/restart-dev-stack.sh
```

For strategy execution outside the web UI, continue using:

```bash
./deploy.sh --strategy adaptive_rotation --mode backtest
```
"""
    )


if __name__ == "__main__":
    main()

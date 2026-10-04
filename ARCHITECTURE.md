# Architecture

## Layering rule

- `frontend/` must never import from `backend/agents/*` or `backend/orchestrator/*`.
  It uses only `backend.services.chat_service` and `backend.models`.
- `backend/` must never import `streamlit`. Secrets from `st.secrets` are read
  lazily in `backend/config.py` through a guarded import.

## Components
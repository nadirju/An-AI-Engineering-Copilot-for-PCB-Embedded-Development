# Deployment

## Local

1. Python 3.11+
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`
4. `streamlit run app.py`

## Streamlit Community Cloud

1. Push the repository to GitHub.
2. Create a new app pointing at `app.py`.
3. In **Settings -> Secrets** add:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
LLM_PROVIDER = "anthropic"
EMBEDDING_PROVIDER = "openai"
OPENAI_API_KEY = "sk-..."
CHROMA_MODE = "memory"
```

4. Deploy. The seed documents are ingested into the in-memory Chroma store
   at startup.

## Environment variables

| Variable | Default | Notes |
|----------|---------|-------|
| `LLM_PROVIDER` | `anthropic` | `anthropic` or `openai` |
| `EMBEDDING_PROVIDER` | `openai` | `openai` or `hash` (offline, no key) |
| `ANTHROPIC_API_KEY` | - | required for Anthropic |
| `OPENAI_API_KEY` | - | required for OpenAI LLM/embeddings |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-5` | override as needed |
| `OPENAI_MODEL` | `gpt-4o` | |
| `CHROMA_MODE` | `persistent` | `persistent` or `memory` |
| `CHROMA_PATH` | `./data/chroma` | |
| `MAX_REVISIONS` | `2` | validation bounce limit |
| `LOG_LEVEL` | `INFO` | |

## Memory

Target under 300 MB. Use `EMBEDDING_PROVIDER=hash` to avoid local model
downloads; no torch dependency is required.
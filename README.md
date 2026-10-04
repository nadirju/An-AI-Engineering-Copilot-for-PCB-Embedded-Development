# Agentic AI Hardware Engineering Copilot

**One AI. Every hardware development workflow.**

An advisory-only agentic copilot for PCB designers, embedded firmware developers, students, and hobbyists. It gives tool-aware, version-aware, hardware-aware guidance inside **Altium Designer**, **KiCad**, **STM32CubeIDE/CubeMX**, and **ESP-IDF**.

Every important answer addresses four questions:

1. What should I do?
2. Why should I do it?
3. How do I verify it?
4. What if it doesn't work?

The copilot never takes physical or external actions on your behalf.

## Interaction modes

| Mode | Purpose |
|------|---------|
| Ask | Understand a tool or concept |
| Guide Me | Step-by-step task completion |
| Show Me | Visual guidance from an uploaded screenshot |
| Generate | Produce implementation, configuration, or code |
| Debug | Systematically isolate a failure |
| Translate | Map a workflow between tools |

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add ANTHROPIC_API_KEY
streamlit run app.py
```

On first run the seed documents in `data/docs/` are ingested into ChromaDB
(`./data/chroma/`). Ingestion is idempotent.

## Demo path

1. Set the project context: STM32F401 + BME280 + SPI + Altium or KiCad.
2. Choose **Guide Me** and ask: "How do I configure SPI in STM32CubeIDE?"
3. Switch to **Generate** and ask for SPI/CS routing constraints for the PCB.
4. Switch to **Debug**, describe an error or upload a logic-analyzer screenshot.

## Tests

```bash
pytest -q
```

## Layout

- `backend/` - models, LLM clients, RAG, agents, LangGraph orchestrator, services
- `frontend/` - Streamlit UI (talks only to `backend.services.chat_service` and `backend.models`)
- `prompts/` - all agent prompts
- `data/docs/` - seed knowledge documents
- `tests/` - pytest suite

See `ARCHITECTURE.md` and `DEPLOYMENT.md` for details.

## License

MIT
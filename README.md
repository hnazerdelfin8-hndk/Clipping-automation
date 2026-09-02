# AI Clipping Automation

Clean FastAPI foundation for the AI clipping pipeline.

## Run

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Verify

- `GET /api/health` must return JSON with `status: ok`.
- `GET /api/test-json` must return `application/json`.
- Run `pytest` to execute the integrity tests.

No real API keys belong in this repository. Use `.env` locally from `.env.example`.

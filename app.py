from pathlib import Path
import json
from fastapi import FastAPI
from fastapi.responses import JSONResponse

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="AI Clipping Automation", version="1.0.0")

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "ai-clipping-automation"}

@app.get("/api/test-json")
def test_json():
    payload = {"status": "ok", "format": "json", "html": False}
    serialized = json.dumps(payload)
    parsed = json.loads(serialized)
    return JSONResponse(content=parsed)

@app.get("/")
def home():
    return {"message": "AI Clipping Automation is running"}

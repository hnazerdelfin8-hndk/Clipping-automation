from pathlib import Path
import json
import shutil

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from core.video import probe_video

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
INPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="AI Clipping Automation", version="1.0.0")

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "ai-clipping-automation"}


@app.get("/api/test-json")
def test_json():
    payload = {"status": "ok", "format": "json", "html": False}
    serialized = json.dumps(payload)
    parsed = json.loads(serialized)
    return JSONResponse(content=parsed)


@app.post("/api/upload-video")
def upload_video(file: UploadFile = File(...)):
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()

    if not filename or extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported video format")

    destination = INPUT_DIR / filename
    with destination.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    try:
        metadata = probe_video(destination)
    except Exception as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Invalid video: {exc}") from exc

    return {"status": "ok", "video": metadata}


@app.get("/")
def home():
    return {"message": "AI Clipping Automation is running"}

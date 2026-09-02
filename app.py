from pathlib import Path
import json
import shutil

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

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


@app.get("/upload", response_class=HTMLResponse)
def upload_page():
    return """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AI Clipping Automation - Upload Test</title>
    <style>
        body { font-family: sans-serif; max-width: 680px; margin: 40px auto; padding: 20px; }
        .box { border: 1px solid #ccc; border-radius: 12px; padding: 24px; }
        button { margin-top: 16px; padding: 12px 18px; cursor: pointer; }
        pre { white-space: pre-wrap; background: #f5f5f5; padding: 12px; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="box">
        <h1>Video Upload Test</h1>
        <p>Select a video to test the backend upload endpoint.</p>
        <input id="video" type="file" accept="video/mp4,video/quicktime,video/x-matroska,video/webm,video/x-msvideo">
        <br>
        <button id="upload" type="button">Upload Video</button>
        <pre id="result">Waiting for video...</pre>
    </div>
    <script>
        const input = document.getElementById('video');
        const button = document.getElementById('upload');
        const result = document.getElementById('result');

        button.addEventListener('click', async () => {
            if (!input.files.length) {
                result.textContent = 'Please select a video first.';
                return;
            }
            const form = new FormData();
            form.append('file', input.files[0]);
            result.textContent = 'Uploading and checking video...';
            try {
                const response = await fetch('/api/upload-video', { method: 'POST', body: form });
                const data = await response.json();
                result.textContent = JSON.stringify(data, null, 2);
            } catch (error) {
                result.textContent = JSON.stringify({status: 'error', message: error.message}, null, 2);
            }
        });
    </script>
</body>
</html>"""


@app.get("/")
def home():
    return {"message": "AI Clipping Automation is running"}

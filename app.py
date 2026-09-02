from pathlib import Path
import json
import shutil
import uuid

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse

from core.video import probe_video

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
UPLOAD_DIR = BASE_DIR / ".uploads"
INPUT_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

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


@app.post("/api/upload-chunk")
def upload_chunk(
    file: UploadFile = File(...),
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
):
    if not upload_id or not upload_id.isalnum() or len(upload_id) > 64:
        raise HTTPException(status_code=400, detail="Invalid upload ID")
    if chunk_index < 0:
        raise HTTPException(status_code=400, detail="Invalid chunk index")

    upload_path = UPLOAD_DIR / upload_id
    upload_path.mkdir(exist_ok=True)
    chunk_path = upload_path / f"{chunk_index:08d}.part"

    with chunk_path.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    return {"status": "ok", "upload_id": upload_id, "chunk_index": chunk_index}


@app.post("/api/complete-upload")
def complete_upload(
    upload_id: str = Form(...),
    filename: str = Form(...),
    total_chunks: int = Form(...),
):
    if not upload_id or not upload_id.isalnum() or len(upload_id) > 64:
        raise HTTPException(status_code=400, detail="Invalid upload ID")
    if total_chunks < 1:
        raise HTTPException(status_code=400, detail="Invalid chunk count")

    safe_filename = Path(filename).name
    extension = Path(safe_filename).suffix.lower()
    if not safe_filename or extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported video format")

    upload_path = UPLOAD_DIR / upload_id
    destination = INPUT_DIR / safe_filename

    try:
        with destination.open("wb") as output:
            for index in range(total_chunks):
                chunk_path = upload_path / f"{index:08d}.part"
                if not chunk_path.is_file():
                    raise HTTPException(status_code=400, detail=f"Missing chunk {index}")
                with chunk_path.open("rb") as chunk:
                    shutil.copyfileobj(chunk, output)

        metadata = probe_video(destination)
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except Exception as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Invalid video: {exc}") from exc
    finally:
        shutil.rmtree(upload_path, ignore_errors=True)

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
        progress { width: 100%; margin-top: 16px; }
        pre { white-space: pre-wrap; background: #f5f5f5; padding: 12px; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="box">
        <h1>Video Upload Test</h1>
        <p>Large videos are uploaded in small chunks to avoid request-size limits.</p>
        <input id="video" type="file" accept="video/mp4,video/quicktime,video/x-matroska,video/webm,video/x-msvideo">
        <br>
        <button id="upload" type="button">Upload Video</button>
        <progress id="progress" value="0" max="100"></progress>
        <pre id="result">Waiting for video...</pre>
    </div>
    <script>
        const input = document.getElementById('video');
        const button = document.getElementById('upload');
        const progress = document.getElementById('progress');
        const result = document.getElementById('result');
        const CHUNK_SIZE = 8 * 1024 * 1024;

        async function jsonOrText(response) {
            const text = await response.text();
            try { return JSON.parse(text); }
            catch { return {status: 'error', http_status: response.status, response: text.slice(0, 1000)}; }
        }

        button.addEventListener('click', async () => {
            if (!input.files.length) {
                result.textContent = 'Please select a video first.';
                return;
            }

            const video = input.files[0];
            const uploadId = crypto.randomUUID().replaceAll('-', '');
            const totalChunks = Math.ceil(video.size / CHUNK_SIZE);
            result.textContent = `Uploading ${video.name} (${(video.size / 1024 / 1024).toFixed(1)} MB)...`;
            button.disabled = true;
            progress.value = 0;

            try {
                for (let index = 0; index < totalChunks; index++) {
                    const start = index * CHUNK_SIZE;
                    const chunk = video.slice(start, Math.min(start + CHUNK_SIZE, video.size));
                    const form = new FormData();
                    form.append('file', chunk, `chunk-${index}.part`);
                    form.append('upload_id', uploadId);
                    form.append('chunk_index', index);

                    const response = await fetch('/api/upload-chunk', { method: 'POST', body: form });
                    const data = await jsonOrText(response);
                    if (!response.ok || data.status !== 'ok') throw new Error(JSON.stringify(data));
                    progress.value = ((index + 1) / totalChunks) * 100;
                    result.textContent = `Uploaded chunk ${index + 1} of ${totalChunks}...`;
                }

                const complete = new FormData();
                complete.append('upload_id', uploadId);
                complete.append('filename', video.name);
                complete.append('total_chunks', totalChunks);
                const response = await fetch('/api/complete-upload', { method: 'POST', body: complete });
                const data = await jsonOrText(response);
                result.textContent = JSON.stringify(data, null, 2);
            } catch (error) {
                result.textContent = JSON.stringify({status: 'error', message: error.message}, null, 2);
            } finally {
                button.disabled = false;
            }
        });
    </script>
</body>
</html>"""


@app.get("/")
def home():
    return {"message": "AI Clipping Automation is running"}

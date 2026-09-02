from pathlib import Path
import json
import subprocess


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}


def probe_video(path: str | Path) -> dict:
    """Return basic metadata for a video using ffprobe."""
    video_path = Path(path)
    if not video_path.is_file():
        raise FileNotFoundError(f"Video not found: {video_path}")
    if video_path.suffix.lower() not in VIDEO_EXTENSIONS:
        raise ValueError(f"Unsupported video format: {video_path.suffix}")

    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration,size:stream=codec_name,width,height",
            "-of", "json",
            str(video_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    video_stream = next((s for s in streams if "width" in s), {})
    fmt = data.get("format", {})

    return {
        "filename": video_path.name,
        "duration": float(fmt["duration"]) if fmt.get("duration") else None,
        "size": int(fmt["size"]) if fmt.get("size") else None,
        "codec": video_stream.get("codec_name"),
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
    }

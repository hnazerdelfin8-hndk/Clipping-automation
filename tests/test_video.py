from pathlib import Path

import pytest

from core.video import probe_video


def test_probe_video_rejects_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        probe_video(tmp_path / "missing.mp4")


def test_probe_video_rejects_unsupported_format(tmp_path: Path):
    path = tmp_path / "test.txt"
    path.write_text("not a video")
    with pytest.raises(ValueError):
        probe_video(path)

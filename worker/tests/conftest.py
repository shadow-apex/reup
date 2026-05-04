import shutil
import subprocess
from pathlib import Path

import pytest


def _ffmpeg_exe() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        pytest.skip("ffmpeg not on PATH")
    return exe


@pytest.fixture
def tiny_mp4(tmp_path: Path) -> Path:
    out = tmp_path / "tiny.mp4"
    ff = _ffmpeg_exe()
    cmd = [
        ff,
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=320x240:rate=1",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:sample_rate=44100",
        "-t",
        "1",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        pytest.skip(f"ffmpeg required to build fixture: {r.stderr}")
    return out


@pytest.fixture
def silent_mp3(tmp_path: Path) -> Path:
    out = tmp_path / "silent.mp3"
    ff = _ffmpeg_exe()
    cmd = [
        ff,
        "-y",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=44100:cl=mono",
        "-t",
        "1",
        "-q:a",
        "9",
        "-acodec",
        "libmp3lame",
        str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        pytest.skip(f"ffmpeg required: {r.stderr}")
    return out

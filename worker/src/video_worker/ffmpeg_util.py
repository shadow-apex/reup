import logging
import subprocess
import threading
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FFmpegResult:
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool


class FFmpegError(Exception):
    def __init__(self, message: str, *, exit_code: int | None = None, stderr: str = ""):
        super().__init__(message)
        self.exit_code = exit_code
        self.stderr = stderr


class FFmpegTimeoutError(Exception):
    pass


def run_ffmpeg(
    args: list[str],
    *,
    ffmpeg_path: str = "ffmpeg",
    timeout_seconds: int = 3600,
) -> FFmpegResult:
    """
    Run ffmpeg with timeout. args must NOT include leading 'ffmpeg' (it is prepended).
    Raises FFmpegTimeoutError on timeout; does not raise on non-zero exit (caller checks).
    """
    cmd = [ffmpeg_path, "-hide_banner", "-nostats", *args]
    logger.info("ffmpeg: %s", " ".join(cmd))
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    timed_out = threading.Event()

    def _kill():
        if proc.poll() is None:
            timed_out.set()
            proc.kill()

    timer = threading.Timer(timeout_seconds, _kill)
    timer.start()
    try:
        stdout, stderr = proc.communicate()
    finally:
        timer.cancel()

    if timed_out.is_set():
        raise FFmpegTimeoutError(f"ffmpeg exceeded {timeout_seconds}s timeout")

    return FFmpegResult(
        exit_code=proc.returncode,
        stdout=stdout or "",
        stderr=stderr or "",
        timed_out=False,
    )


def require_ffmpeg_ok(result: FFmpegResult, *, context: str) -> None:
    if result.exit_code != 0:
        tail = (result.stderr or "")[-4000:]
        raise FFmpegError(
            f"{context}: ffmpeg exit {result.exit_code}",
            exit_code=result.exit_code if result.exit_code is not None else -1,
            stderr=tail,
        )

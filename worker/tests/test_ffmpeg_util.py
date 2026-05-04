import pytest

from video_worker.ffmpeg_util import FFmpegError, FFmpegResult, require_ffmpeg_ok


def test_require_ffmpeg_ok_raises_with_exit_code():
    r = FFmpegResult(exit_code=1, stdout="", stderr="mock stderr", timed_out=False)
    with pytest.raises(FFmpegError) as ei:
        require_ffmpeg_ok(r, context="test")
    assert ei.value.exit_code == 1

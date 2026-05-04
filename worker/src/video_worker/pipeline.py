from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path

import edge_tts
import httpx

from video_worker.errors import ContractError
from video_worker.ffmpeg_util import FFmpegError, FFmpegTimeoutError, require_ffmpeg_ok, run_ffmpeg
from video_worker.settings import Settings

logger = logging.getLogger(__name__)


async def translate_text(text: str, settings: Settings, source: str, target: str) -> str:
    if not settings.openai_api_key.strip():
        raise ContractError(
            "TRANSLATE_ERROR",
            "OPENAI_API_KEY is empty",
            detail="Set OPENAI_API_KEY for PIPELINE_MODE=real",
        )
    url = settings.openai_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.openai_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    f"You translate video narration from {source} to {target}. "
                    "Output only the translated text, same tone, no quotes."
                ),
            },
            {"role": "user", "content": text},
        ],
        "temperature": 0.3,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            url,
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json=payload,
        )
    if r.status_code >= 400:
        raise ContractError(
            "TRANSLATE_ERROR",
            "Translation API request failed",
            detail=r.text[:2000],
        )
    data = r.json()
    try:
        return str(data["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as e:
        raise ContractError(
            "TRANSLATE_ERROR",
            "Unexpected translation API response",
            detail=str(e),
        ) from e


async def _edge_tts_to_file(text: str, out_mp3: Path, voice: str) -> None:
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(out_mp3))
    except Exception as e:
        raise ContractError(
            "TTS_ERROR",
            "Text-to-speech failed",
            detail=str(e)[:2000],
        ) from e


def _asr_faster_whisper(wav_path: Path, settings: Settings) -> str:
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise ContractError(
            "ASR_ERROR",
            "faster-whisper not installed",
            detail="pip install -e '.[asr]'",
        ) from e

    model = WhisperModel(
        settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )
    segments, _info = model.transcribe(str(wav_path), language=None)
    parts: list[str] = []
    for seg in segments:
        parts.append(seg.text.strip())
    return " ".join(parts).strip() or "."


def _extract_audio_sync(
    input_video: Path,
    out_wav: Path,
    settings: Settings,
) -> None:
    result = run_ffmpeg(
        [
            "-y",
            "-i",
            str(input_video),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(out_wav),
        ],
        ffmpeg_path=settings.ffmpeg_path,
        timeout_seconds=settings.ffmpeg_timeout_seconds,
    )
    require_ffmpeg_ok(result, context="extract audio")


def _mux_video_audio_sync(
    input_video: Path,
    audio_mp3: Path,
    output_mp4: Path,
    settings: Settings,
) -> None:
    result = run_ffmpeg(
        [
            "-y",
            "-i",
            str(input_video),
            "-i",
            str(audio_mp3),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(output_mp4),
        ],
        ffmpeg_path=settings.ffmpeg_path,
        timeout_seconds=settings.ffmpeg_timeout_seconds,
    )
    require_ffmpeg_ok(result, context="mux video+audio")


async def run_pipeline(
    *,
    job_id: str,
    input_video_path: str,
    output_dir: str,
    source_language: str,
    target_language: str,
    settings: Settings,
) -> tuple[str, str | None]:
    """
    Returns (output_video_path, message). Raises ContractError on failure.
    """
    input_video = Path(input_video_path)
    out_dir = Path(output_dir)
    if not input_video.is_file():
        raise ContractError(
            "PIPELINE_ERROR",
            "Input video not found",
            detail=str(input_video),
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    output_mp4 = out_dir / f"{job_id}.mp4"

    if settings.pipeline_mode == "stub":
        text_vi = "Đây là bản thử nghiệm chế độ stub. Stub mode không dùng nhận dạng giọng nói."
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            mp3 = tdir / "narration.mp3"
            await _edge_tts_to_file(text_vi, mp3, settings.edge_tts_voice)

            def _stub_mux() -> None:
                _mux_video_audio_sync(input_video, mp3, output_mp4, settings)

            await asyncio.to_thread(_stub_mux)
        return str(output_mp4), "Stub pipeline: Vietnamese placeholder narration muxed."

    # real pipeline
    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)
        wav = tdir / "audio.wav"
        mp3 = tdir / "narration.mp3"

        def _extract() -> None:
            _extract_audio_sync(input_video, wav, settings)

        await asyncio.to_thread(_extract)

        def _asr() -> str:
            return _asr_faster_whisper(wav, settings)

        zh_text = await asyncio.to_thread(_asr)
        if not zh_text.strip():
            raise ContractError("ASR_ERROR", "Empty transcript", detail="")

        vi_text = await translate_text(zh_text, settings, source_language, target_language)
        await _edge_tts_to_file(vi_text, mp3, settings.edge_tts_voice)

        def _mux() -> None:
            _mux_video_audio_sync(input_video, mp3, output_mp4, settings)

        await asyncio.to_thread(_mux)

    return str(output_mp4), "Real pipeline: ASR -> translate -> TTS -> mux."


def contract_error_from_exception(exc: BaseException) -> ContractError:
    if isinstance(exc, ContractError):
        return exc
    if isinstance(exc, FFmpegTimeoutError):
        return ContractError(
            "FFMPEG_TIMEOUT",
            str(exc),
            detail=str(exc),
            ffmpeg_exit_code=None,
        )
    if isinstance(exc, FFmpegError):
        return ContractError(
            "FFMPEG_ERROR",
            str(exc),
            detail=exc.stderr[:2000] if exc.stderr else None,
            ffmpeg_exit_code=exc.exit_code,
        )
    return ContractError(
        "PIPELINE_ERROR",
        "Unexpected pipeline error",
        detail=str(exc)[:2000],
    )

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

MAX_TTS_CHARS = 500


def _split_text(text: str, max_chars: int = MAX_TTS_CHARS) -> list[str]:
    """Split text into chunks at sentence boundaries, each <= max_chars."""
    import re
    sentences = re.split(r'(?<=[.。!！?？])', text)
    chunks: list[str] = []
    current = ""
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if len(current) + len(s) <= max_chars:
            current += s + " "
        else:
            if current:
                chunks.append(current.strip())
            current = s + " "
    if current:
        chunks.append(current.strip())
    return chunks or [text[:max_chars]]


async def translate_text(text: str, settings: Settings, source: str, target: str,
                         *,
                         api_key_override: str | None = None,
                         base_url_override: str | None = None,
                         model_override: str | None = None) -> str:
    api_key = (api_key_override or settings.openai_api_key).strip()
    if not api_key:
        raise ContractError(
            "TRANSLATE_ERROR",
            "OPENAI_API_KEY is empty — set it in .env or send openai_api_key in the job request",
            detail="",
        )
    base_url = (base_url_override or settings.openai_base_url).rstrip("/")
    model = model_override or settings.openai_model
    url = base_url + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a professional video narration translator. "
                    f"Translate the following {source} narration into natural {target}. "
                    "The output must sound fluent and natural when spoken aloud. "
                    "Adapt idioms and cultural references, don't translate them literally. "
                    "Preserve the original speaker's tone (serious, casual, excited, etc.). "
                    "Output ONLY the translated text, no explanations, no quotation marks."
                ),
            },
            {"role": "user", "content": text},
        ],
        "temperature": 0.3,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
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


async def _edge_tts_save(text: str, out_mp3: Path, voice: str, max_retries: int = 3) -> None:
    """Try edge-tts with retries. Returns normally on success, raises on failure."""
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(out_mp3))
            return
        except Exception as e:
            last_exc = e
            if attempt + 1 < max_retries:
                logger.warning("edge-tts attempt %d/%d failed: %s", attempt + 1, max_retries, e)
                await asyncio.sleep(2 ** attempt)
    raise ContractError(
        "TTS_ERROR",
        "Text-to-speech (edge-tts) failed after retries",
        detail=str(last_exc)[:2000],
    ) from last_exc


def _gtts_save(text: str, out_mp3: Path) -> None:
    """Fallback TTS via Google (gTTS). Runs in a thread (it's synchronous)."""
    try:
        from gtts import gTTS
    except ImportError:
        raise ContractError(
            "TTS_ERROR",
            "gTTS fallback not available",
            detail="pip install gTTS",
        )
    tts = gTTS(text, lang="vi")
    tts.save(str(out_mp3))


async def _tts_to_file(text: str, out_mp3: Path, voice: str) -> None:
    """Generate TTS, splitting long text into chunks and concatenating via ffmpeg.

    Tries edge-tts first (with retries), falls back to gTTS if it fails.
    """
    chunks = _split_text(text)

    async def _try_provider(provider_label: str) -> bool:
        """Returns True on success, False if provider is unavailable to fall back."""
        if len(chunks) == 1:
            try:
                if provider_label == "edge-tts":
                    await _edge_tts_save(text, out_mp3, voice)
                else:
                    await asyncio.to_thread(_gtts_save, text, out_mp3)
                return True
            except ContractError:
                return False

        # Multiple chunks: generate each, then concat via ffmpeg
        chunk_files: list[Path] = []
        parent = out_mp3.parent
        try:
            for i, chunk in enumerate(chunks):
                tmp = parent / f"chunk_{i:04d}.mp3"
                if provider_label == "edge-tts":
                    await _edge_tts_save(chunk, tmp, voice)
                else:
                    await asyncio.to_thread(_gtts_save, chunk, tmp)
                chunk_files.append(tmp)

            # ffmpeg concat
            list_path = parent / "concat.txt"
            list_path.write_text(
                "\n".join(f"file '{c.name}'" for c in chunk_files),
                encoding="utf-8",
            )
            from video_worker.settings import get_settings
            st = get_settings()
            result = run_ffmpeg(
                ["-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", str(out_mp3)],
                ffmpeg_path=st.ffmpeg_path,
                timeout_seconds=st.ffmpeg_timeout_seconds,
            )
            require_ffmpeg_ok(result, context="TTS concat chunks")
            return True
        except ContractError:
            return False
        except Exception as e:
            logger.warning("TTS %s failed: %s", provider_label, e)
            return False
        finally:
            for f in chunk_files:
                try:
                    f.unlink(missing_ok=True)
                except OSError:
                    pass

    # Try edge-tts first, then gTTS
    if await _try_provider("edge-tts"):
        return
    logger.warning("edge-tts failed, falling back to gTTS")
    if await _try_provider("gtts"):
        logger.info("gTTS fallback succeeded")
        return
    raise ContractError("TTS_ERROR", "All TTS providers failed")


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
    *,
    vol_orig: float = 0.15,
) -> None:
    result = run_ffmpeg(
        [
            "-y",
            "-i",
            str(input_video),
            "-i",
            str(audio_mp3),
            "-filter_complex",
            (
                f"[0:a:0]volume={vol_orig}[orig];"
                "[1:a:0]volume=1.0[tts];"
                "[orig][tts]amix=inputs=2:duration=first[outa]"
            ),
            "-map",
            "0:v:0",
            "-map",
            "[outa]",
            "-c:v",
            "libx264",
            "-crf",
            "23",
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
    # per-job overrides (None = use settings defaults)
    openai_base_url: str | None = None,
    openai_api_key: str | None = None,
    openai_model: str | None = None,
    vol_orig: float | None = None,
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

    # resolve volume
    orig_vol = vol_orig if vol_orig is not None else 0.15

    if settings.pipeline_mode == "stub":
        text_vi = "Đây là bản thử nghiệm chế độ stub. Stub mode không dùng nhận dạng giọng nói."
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            mp3 = tdir / "narration.mp3"
            await _tts_to_file(text_vi, mp3, settings.edge_tts_voice)

            def _stub_mux() -> None:
                _mux_video_audio_sync(input_video, mp3, output_mp4, settings, vol_orig=orig_vol)

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

        vi_text = await translate_text(
            zh_text, settings, source_language, target_language,
            api_key_override=openai_api_key,
            base_url_override=openai_base_url,
            model_override=openai_model,
        )
        await _tts_to_file(vi_text, mp3, settings.edge_tts_voice)

        def _mux() -> None:
            _mux_video_audio_sync(input_video, mp3, output_mp4, settings, vol_orig=orig_vol)

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

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
from video_worker.srt_utils import (
    SRTSegment,
    build_translation_prompt,
    make_translated_segments,
    parse_srt,
    parse_translation_response,
    segments_to_srt,
    write_srt,
)

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


async def _chat_completion(
    system_prompt: str,
    user_content: str,
    settings: Settings,
    *,
    api_key_override: str | None = None,
    base_url_override: str | None = None,
    model_override: str | None = None,
    temperature: float = 0.3,
) -> str:
    """Shared low-level call to an OpenAI-compatible /chat/completions endpoint."""
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
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": temperature,
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


async def translate_text(text: str, settings: Settings, source: str, target: str,
                         *,
                         api_key_override: str | None = None,
                         base_url_override: str | None = None,
                         model_override: str | None = None) -> str:
    system_prompt = (
        "You are a professional video narration translator. "
        f"Translate the following {source} narration into natural {target}. "
        "The output must sound fluent and natural when spoken aloud. "
        "Adapt idioms and cultural references, don't translate them literally. "
        "Preserve the original speaker's tone (serious, casual, excited, etc.). "
        "Output ONLY the translated text, no explanations, no quotation marks."
    )
    return await _chat_completion(
        system_prompt, text, settings,
        api_key_override=api_key_override,
        base_url_override=base_url_override,
        model_override=model_override,
    )


async def translate_srt_segments(
    segments: list,
    settings: Settings,
    source: str,
    target: str,
    *,
    api_key_override: str | None = None,
    base_url_override: str | None = None,
    model_override: str | None = None,
) -> list[SRTSegment]:
    """Translate a list of ASR/SRT segments while preserving their ORIGINAL
    timestamps. This is the fix for the previous behaviour, which joined all
    segment text into a single blob before translating and therefore lost the
    ability to map translated text back onto per-line timing.

    Strategy: send every line as a numbered list in ONE request so the model
    keeps a 1:1 line correspondence (cheap and keeps context across lines for
    a more natural translation). If the model drops/merges some lines, the
    missing ones are translated individually as a fallback so we never end
    up with a wrong segment count or a timing drift.
    """
    numbered_source = build_translation_prompt(segments)
    system_prompt = (
        "You are a professional subtitle translator. "
        f"Translate the following numbered {source} subtitle lines into natural, "
        f"spoken-style {target}. "
        "You MUST return the SAME NUMBER of lines, each starting with its "
        "original number followed by a period (e.g. '1. ...'), one line per "
        "subtitle — do NOT merge, split, add, or remove lines, and do not add "
        "any commentary before or after the list."
    )
    raw_response = await _chat_completion(
        system_prompt, numbered_source, settings,
        api_key_override=api_key_override,
        base_url_override=base_url_override,
        model_override=model_override,
    )
    translations = parse_translation_response(raw_response, len(segments))

    missing = [i for i in range(1, len(segments) + 1) if not translations.get(i, "").strip()]
    if missing:
        logger.warning(
            "Batch SRT translation missing %d/%d lines, translating individually",
            len(missing), len(segments),
        )
        for i in missing:
            seg = segments[i - 1]
            seg_text = seg.text if hasattr(seg, "text") else seg[2]
            if not seg_text.strip():
                continue
            try:
                translations[i] = await translate_text(
                    seg_text, settings, source, target,
                    api_key_override=api_key_override,
                    base_url_override=base_url_override,
                    model_override=model_override,
                )
            except ContractError as e:
                logger.warning("Fallback translation failed for line %d: %s", i, e)

    return make_translated_segments(segments, translations)


async def _edge_tts_save(
    text: str,
    out_mp3: Path,
    voice: str,
    rate: str = "+0%",
    pitch: str = "+0Hz",
    max_retries: int = 3,
) -> None:
    """Try edge-tts with retries. Returns normally on success, raises on failure."""
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
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


async def _tts_to_file(
    text: str,
    out_mp3: Path,
    voice: str,
    rate: str = "+0%",
    pitch: str = "+0Hz",
) -> None:
    """Generate TTS, splitting long text into chunks and concatenating via ffmpeg.

    Tries edge-tts first (with retries), falls back to gTTS if it fails.
    """
    chunks = _split_text(text)

    async def _try_provider(provider_label: str) -> bool:
        """Returns True on success, False if provider is unavailable to fall back."""
        if len(chunks) == 1:
            try:
                if provider_label == "edge-tts":
                    await _edge_tts_save(text, out_mp3, voice, rate, pitch)
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
                    await _edge_tts_save(chunk, tmp, voice, rate, pitch)
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


async def _tts_segments_synced(
    segments: list[SRTSegment],
    out_audio: Path,
    voice: str,
    settings: Settings,
    rate: str = "+0%",
    pitch: str = "+0Hz",
) -> None:
    """Generate TTS per translated segment and place each one at its ORIGINAL
    start time on the timeline using ffmpeg's `adelay` filter, then mix all
    lines into a single track written to `out_audio`.

    This replaces the old behaviour of concatenating all narration into one
    continuous track (which drifted out of sync with the video the moment
    total TTS duration differed from total original speech duration). Here
    every line stays anchored to its own timestamp, same as the subtitle it
    corresponds to.

    Requires ffmpeg >= 4.4 (adelay's `all=1` option).
    """
    usable = [seg for seg in segments if seg.text.strip()]
    if not usable:
        raise ContractError("TTS_ERROR", "No translated text to synthesize", detail="")

    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)
        chunk_paths: list[tuple[float, Path]] = []
        for i, seg in enumerate(usable):
            tmp = tdir / f"seg_{i:04d}.mp3"
            await _tts_to_file(seg.text, tmp, voice, rate, pitch)
            chunk_paths.append((seg.start, tmp))

        input_args: list[str] = []
        for _, f in chunk_paths:
            input_args += ["-i", str(f)]

        if len(chunk_paths) == 1:
            delay_ms = max(0, int(chunk_paths[0][0] * 1000))
            filter_complex = f"[0:a:0]adelay={delay_ms}:all=1[outa]"
        else:
            delay_parts = []
            mix_labels = []
            for idx, (start, _) in enumerate(chunk_paths):
                delay_ms = max(0, int(start * 1000))
                delay_parts.append(f"[{idx}:a:0]adelay={delay_ms}:all=1[d{idx}]")
                mix_labels.append(f"[d{idx}]")
            filter_complex = (
                ";".join(delay_parts)
                + ";"
                + "".join(mix_labels)
                + f"amix=inputs={len(chunk_paths)}:duration=longest:dropout_transition=0,volume={len(chunk_paths)}[outa]"
            )

        result = run_ffmpeg(
            ["-y", *input_args, "-filter_complex", filter_complex, "-map", "[outa]",
             "-ar", "44100", str(out_audio)],
            ffmpeg_path=settings.ffmpeg_path,
            timeout_seconds=settings.ffmpeg_timeout_seconds,
        )
        require_ffmpeg_ok(result, context="synced TTS mix")


def _asr_faster_whisper(wav_path: Path, settings: Settings) -> tuple[str, list]:
    """ASR with timestamps. Returns (full_text, segments_list)."""
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
    segments = list(segments)  # Convert generator to list

    parts: list[str] = []
    for seg in segments:
        parts.append(seg.text.strip())

    full_text = " ".join(parts).strip() or "."
    return full_text, segments


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
    audio_track: Path,
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
            str(audio_track),
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
    # ✅ Nếu được cung cấp: bỏ qua ASR + gọi API dịch hoàn toàn, dùng thẳng
    # file SRT NÀY (đã dịch sẵn thủ công, ví dụ dán cho ChatGPT dịch rồi
    # lưu lại) làm nguồn timestamp + text để TTS đồng bộ + ghép video.
    translated_srt_path: str | None = None,
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

    # ─── Chế độ "SRT đã dịch sẵn" — KHÔNG gọi ASR, KHÔNG gọi API dịch ───
    if translated_srt_path:
        srt_path = Path(translated_srt_path)
        if not srt_path.is_file():
            raise ContractError(
                "PIPELINE_ERROR",
                "Translated SRT not found",
                detail=str(srt_path),
            )
        translated_segments = parse_srt(srt_path)
        if not translated_segments:
            raise ContractError("PIPELINE_ERROR", "Translated SRT is empty or malformed", detail=str(srt_path))

        # Lưu lại 1 bản sao trong output dir cho nhất quán với các job khác
        srt_vi_path = out_dir / f"{job_id}_vi.srt"
        write_srt(translated_segments, srt_vi_path)
        vi_text = " ".join(seg.text for seg in translated_segments).strip()
        txt_vi_path = out_dir / f"{job_id}_vi.txt"
        txt_vi_path.write_text(vi_text, encoding="utf-8")

        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            narration_track = tdir / "narration_synced.wav"
            await _tts_segments_synced(translated_segments, narration_track, settings.edge_tts_voice, settings, settings.edge_tts_rate, settings.edge_tts_pitch)

            def _mux() -> None:
                _mux_video_audio_sync(input_video, narration_track, output_mp4, settings, vol_orig=orig_vol)

            await asyncio.to_thread(_mux)

        return str(output_mp4), "Manual-SRT pipeline: SRT đã dịch sẵn -> synced TTS -> mux (không dùng API)."

    if settings.pipeline_mode == "stub":
        text_vi = "Đây là bản thử nghiệm chế độ stub. Stub mode không dùng nhận dạng giọng nói."
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            mp3 = tdir / "narration.mp3"
            await _tts_to_file(text_vi, mp3, settings.edge_tts_voice, settings.edge_tts_rate, settings.edge_tts_pitch)

            def _stub_mux() -> None:
                _mux_video_audio_sync(input_video, mp3, output_mp4, settings, vol_orig=orig_vol)

            await asyncio.to_thread(_stub_mux)
        return str(output_mp4), "Stub pipeline: Vietnamese placeholder narration muxed."

    # real pipeline
    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)
        wav = tdir / "audio.wav"
        narration_track = tdir / "narration_synced.wav"

        def _extract() -> None:
            _extract_audio_sync(input_video, wav, settings)

        await asyncio.to_thread(_extract)

        def _asr() -> tuple[str, list]:
            return _asr_faster_whisper(wav, settings)

        zh_text, segments = await asyncio.to_thread(_asr)
        if not zh_text.strip():
            raise ContractError("ASR_ERROR", "Empty transcript", detail="")

        # Export original-language SRT (real ASR timestamps) + plain text
        srt_zh_path = out_dir / f"{job_id}_zh.srt"
        segments_to_srt(segments, srt_zh_path)
        logger.info(f"Exported SRT: {srt_zh_path}")

        txt_zh_path = out_dir / f"{job_id}_zh.txt"
        txt_zh_path.write_text(zh_text, encoding="utf-8")
        logger.info(f"Exported transcript: {txt_zh_path}")

        # Translate PER SEGMENT so the original timestamps can be reused —
        # this is the fix: previously the whole transcript was translated as
        # one blob, which threw away the ability to build a translated SRT.
        translated_segments = await translate_srt_segments(
            segments, settings, source_language, target_language,
            api_key_override=openai_api_key,
            base_url_override=openai_base_url,
            model_override=openai_model,
        )
        vi_text = " ".join(seg.text for seg in translated_segments).strip()
        if not vi_text:
            raise ContractError("TRANSLATE_ERROR", "Empty translation", detail="")

        # Export translated SRT — same start/end as the original, only the
        # text differs, so it stays perfectly in sync with the source.
        srt_vi_path = out_dir / f"{job_id}_vi.srt"
        write_srt(translated_segments, srt_vi_path)
        logger.info(f"Exported translated SRT: {srt_vi_path}")

        txt_vi_path = out_dir / f"{job_id}_vi.txt"
        txt_vi_path.write_text(vi_text, encoding="utf-8")
        logger.info(f"Exported translation: {txt_vi_path}")

        # TTS per segment, each placed at its own timestamp, instead of one
        # continuous narration track — keeps the dubbed audio in sync with
        # both the video and the exported *_vi.srt.
        await _tts_segments_synced(translated_segments, narration_track, settings.edge_tts_voice, settings, settings.edge_tts_rate, settings.edge_tts_pitch)

        def _mux() -> None:
            _mux_video_audio_sync(input_video, narration_track, output_mp4, settings, vol_orig=orig_vol)

        await asyncio.to_thread(_mux)

    return str(output_mp4), "Real pipeline: ASR -> per-segment translate -> synced TTS -> mux."


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
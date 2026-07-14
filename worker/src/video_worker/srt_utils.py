"""Utilities for SRT subtitle file handling with timestamps."""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SRTSegment:
    """Represents a single SRT subtitle segment."""
    index: int
    start: float  # seconds
    end: float  # seconds
    text: str


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _parse_timestamp(ts_str: str) -> float:
    """Parse SRT timestamp (HH:MM:SS,mmm) to seconds."""
    try:
        parts = ts_str.replace(',', '.').split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        secs = float(parts[2])
        return hours * 3600 + minutes * 60 + secs
    except (ValueError, IndexError):
        return 0.0


def segments_to_srt(segments: list, output_srt_path: Path) -> None:
    """Convert faster-whisper segments to SRT format.
    
    Args:
        segments: List of whisper segments with .start, .end, .text attributes
        output_srt_path: Path to write SRT file
    """
    with open(output_srt_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(segments, 1):
            start = _format_timestamp(segment.start)
            end = _format_timestamp(segment.end)
            text = segment.text.strip()
            if text:
                f.write(f"{i}\n{start} --> {end}\n{text}\n\n")


def parse_srt(srt_path: Path) -> list[SRTSegment]:
    """Parse SRT file and return list of segments.
    
    Args:
        srt_path: Path to SRT file
        
    Returns:
        List of SRTSegment objects
    """
    segments = []
    content = srt_path.read_text(encoding='utf-8')
    blocks = content.strip().split('\n\n')
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        
        try:
            index = int(lines[0])
            timestamp = lines[1]
            text = '\n'.join(lines[2:]).strip()
            
            if '-->' in timestamp:
                times = timestamp.split('-->')
                start = _parse_timestamp(times[0].strip())
                end = _parse_timestamp(times[1].strip())
                
                segments.append(SRTSegment(
                    index=index,
                    start=start,
                    end=end,
                    text=text
                ))
        except (ValueError, IndexError):
            continue
    
    return segments


def write_srt(segments: list[SRTSegment], output_path: Path) -> None:
    """Write SRT segments to file.
    
    Args:
        segments: List of SRTSegment objects
        output_path: Path to write SRT file
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, seg in enumerate(segments, 1):
            start = _format_timestamp(seg.start)
            end = _format_timestamp(seg.end)
            f.write(f"{i}\n{start} --> {end}\n{seg.text}\n\n")


def _seg_fields(seg) -> tuple[float, float, str]:
    """Return (start, end, text) whether seg is an SRTSegment, a whisper
    Segment (has .start/.end/.text attrs) or a plain (start, end, text) tuple."""
    if hasattr(seg, "start") and hasattr(seg, "end") and hasattr(seg, "text"):
        return seg.start, seg.end, seg.text
    start, end, text = seg
    return start, end, text


def build_translation_prompt(segments: list) -> str:
    """Turn segments into a numbered list ("1. ...\\n2. ...") suitable for
    sending to a translation LLM in a single request while preserving
    the 1:1 correspondence with the original timestamps.
    """
    lines = []
    for i, seg in enumerate(segments, 1):
        _, _, text = _seg_fields(seg)
        text = " ".join(text.strip().splitlines())
        lines.append(f"{i}. {text}")
    return "\n".join(lines)


def parse_translation_response(response: str, expected_count: int) -> dict[int, str]:
    """Parse a numbered translation response ("1. ...\\n2. ...") back into
    {index: translated_text}. Tolerates the model wrapping a long line onto
    the next physical line (no leading number) by appending it to the
    previous entry.
    """
    result: dict[int, str] = {}
    pattern = re.compile(r'^\s*(\d+)[.\):]\s*(.*)$')
    current_idx = None
    for raw_line in response.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = pattern.match(line)
        if m:
            current_idx = int(m.group(1))
            if 1 <= current_idx <= expected_count:
                result[current_idx] = m.group(2).strip()
            else:
                current_idx = None
        elif current_idx is not None and current_idx in result:
            result[current_idx] += " " + line
    return result


def make_translated_segments(segments: list, translations: dict[int, str]) -> list[SRTSegment]:
    """Combine the ORIGINAL timing of `segments` with translated text.

    This is the key fix: timestamps always come from the source-language
    ASR/SRT segments, never recomputed or estimated — only the text field
    changes. If a translation is missing for some index (model skipped a
    line), the original-language text is kept for that line rather than
    leaving a gap, so timing/count never drifts.
    """
    out = []
    for i, seg in enumerate(segments, 1):
        start, end, original_text = _seg_fields(seg)
        translated = translations.get(i, "").strip()
        out.append(SRTSegment(
            index=i,
            start=start,
            end=end,
            text=translated or original_text,
        ))
    return out


def extract_text_from_srt(srt_path: Path) -> str:
    """Extract plain text from SRT file (join all text parts).
    
    Args:
        srt_path: Path to SRT file
        
    Returns:
        Plain text with all subtitle text joined
    """
    segments = parse_srt(srt_path)
    return " ".join(seg.text for seg in segments)
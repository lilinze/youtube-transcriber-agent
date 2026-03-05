#!/usr/bin/env python3
"""Convert a YouTube video into transcript text.

The script prefers published captions when available and falls back to
downloading audio plus Whisper-based ASR when captions are unavailable.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a YouTube video into plain text."
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "--output",
        default="transcript.txt",
        help="Path to the text transcript output file",
    )
    parser.add_argument(
        "--json-output",
        help="Optional path to structured JSON segment output",
    )
    parser.add_argument(
        "--srt-output",
        help="Optional path to SRT subtitle output",
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "subtitles", "asr"),
        default="auto",
        help="Prefer subtitles, force ASR, or choose automatically",
    )
    parser.add_argument(
        "--language",
        help="Preferred language code for subtitles or ASR, for example en or zh",
    )
    parser.add_argument(
        "--model",
        default="base",
        help="Whisper model size to use for ASR",
    )
    parser.add_argument(
        "--device",
        default="auto",
        help="ASR device hint for faster-whisper, for example auto, cpu, or cuda",
    )
    parser.add_argument(
        "--with-timestamps",
        action="store_true",
        help="Include timestamps in the text transcript",
    )
    parser.add_argument(
        "--keep-audio",
        action="store_true",
        help="Keep the downloaded audio file after ASR finishes",
    )
    return parser.parse_args()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def normalize_segments(raw_segments: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for item in raw_segments:
        start = float(item.get("start", 0.0))
        duration = float(item.get("duration", item.get("end", 0.0) - start))
        end = float(item.get("end", start + duration))
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        segments.append({"start": start, "end": end, "text": text})
    return segments


def format_timestamp(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def render_text(segments: list[dict[str, Any]], with_timestamps: bool) -> str:
    lines: list[str] = []
    for segment in segments:
        text = segment["text"].strip()
        if with_timestamps:
            lines.append(
                f"[{format_timestamp(segment['start'])} - "
                f"{format_timestamp(segment['end'])}] {text}"
            )
        else:
            lines.append(text)
    return "\n".join(lines).strip() + "\n"


def format_srt_timestamp(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def render_srt(segments: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for index, segment in enumerate(segments, start=1):
        start = format_srt_timestamp(segment["start"])
        end = format_srt_timestamp(segment["end"])
        text = segment["text"].strip()
        blocks.append(f"{index}\n{start} --> {end}\n{text}")
    return "\n\n".join(blocks).strip() + "\n"


def try_fetch_subtitles(url: str, language: str | None) -> list[dict[str, Any]] | None:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency: install youtube-transcript-api for subtitle mode."
        ) from exc

    video_id = extract_video_id(url)
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

    candidates: list[str] = []
    if language:
        candidates.append(language)
        if "-" in language:
            candidates.append(language.split("-", 1)[0])
    candidates.extend(["en", "en-US"])

    for lang in candidates:
        try:
            transcript = transcript_list.find_transcript([lang])
            return normalize_segments(transcript.fetch())
        except Exception:
            continue

    try:
        transcript = transcript_list.find_generated_transcript(candidates or ["en"])
        return normalize_segments(transcript.fetch())
    except Exception:
        pass

    for transcript in transcript_list:
        try:
            return normalize_segments(transcript.fetch())
        except Exception:
            continue
    return None


def extract_video_id(url: str) -> str:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()
    path = parsed.path.strip("/")

    if not host:
        raise ValueError(f"Unsupported YouTube URL: {url}")

    if host in {"youtu.be", "www.youtu.be"}:
        if path:
            return path.split("/", 1)[0]
        raise ValueError(f"Unsupported YouTube URL: {url}")

    if host in {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
    }:
        if path == "watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
            if video_id:
                return video_id
        if path.startswith("shorts/"):
            video_id = path.split("/", 1)[1]
            if video_id:
                return video_id
        if path.startswith("live/"):
            video_id = path.split("/", 1)[1]
            if video_id:
                return video_id
        if path.startswith("embed/"):
            video_id = path.split("/", 1)[1]
            if video_id:
                return video_id

    raise ValueError(f"Unsupported YouTube URL: {url}")


def require_binary(name: str) -> None:
    if shutil.which(name):
        return
    raise RuntimeError(f"Required binary not found on PATH: {name}")


def download_audio(url: str, working_dir: Path) -> Path:
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError("Missing dependency: install yt-dlp for ASR mode.") from exc

    require_binary("ffmpeg")
    output_template = str(working_dir / "%(id)s.%(ext)s")
    options = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info["id"]
    audio_path = working_dir / f"{video_id}.mp3"
    if not audio_path.exists():
        raise RuntimeError(f"Audio download failed: {audio_path} was not created.")
    return audio_path


def transcribe_with_faster_whisper(
    audio_path: Path,
    language: str | None,
    model: str,
    device: str,
) -> list[dict[str, Any]]:
    from faster_whisper import WhisperModel

    model_device = device if device != "auto" else "auto"
    whisper_model = WhisperModel(model, device=model_device, compute_type="auto")
    segments, _info = whisper_model.transcribe(
        str(audio_path),
        language=language,
        vad_filter=True,
    )
    return [
        {"start": segment.start, "end": segment.end, "text": segment.text.strip()}
        for segment in segments
        if segment.text.strip()
    ]


def transcribe_with_openai_whisper(
    audio_path: Path, language: str | None, model: str
) -> list[dict[str, Any]]:
    import whisper

    whisper_model = whisper.load_model(model)
    result = whisper_model.transcribe(str(audio_path), language=language)
    return normalize_segments(result.get("segments", []))


def transcribe_audio(
    audio_path: Path, language: str | None, model: str, device: str
) -> list[dict[str, Any]]:
    errors: list[str] = []
    try:
        return transcribe_with_faster_whisper(audio_path, language, model, device)
    except ImportError:
        errors.append("faster-whisper unavailable")
    except Exception as exc:
        errors.append(f"faster-whisper failed: {exc}")

    try:
        return transcribe_with_openai_whisper(audio_path, language, model)
    except ImportError:
        errors.append("openai-whisper unavailable")
    except Exception as exc:
        errors.append(f"openai-whisper failed: {exc}")

    raise RuntimeError(
        "No usable ASR backend found. Install faster-whisper or openai-whisper. "
        + " / ".join(errors)
    )


def write_outputs(
    segments: list[dict[str, Any]],
    text_output: Path,
    json_output: Path | None,
    srt_output: Path | None,
    with_timestamps: bool,
) -> None:
    ensure_parent(text_output)
    text_output.write_text(
        render_text(segments, with_timestamps), encoding="utf-8-sig"
    )
    if json_output:
        ensure_parent(json_output)
        json_output.write_text(
            json.dumps(segments, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if srt_output:
        ensure_parent(srt_output)
        srt_output.write_text(render_srt(segments), encoding="utf-8-sig")


def main() -> int:
    args = parse_args()
    text_output = Path(args.output)
    json_output = Path(args.json_output) if args.json_output else None
    srt_output = Path(args.srt_output) if args.srt_output else None

    segments: list[dict[str, Any]] | None = None
    subtitle_error: Exception | None = None

    if args.mode in {"auto", "subtitles"}:
        try:
            segments = try_fetch_subtitles(args.url, args.language)
        except Exception as exc:
            subtitle_error = exc
        if args.mode == "subtitles" and not segments:
            raise SystemExit(
                f"Subtitle extraction failed: {subtitle_error or 'no transcript found'}"
            )

    if not segments:
        with tempfile.TemporaryDirectory(prefix="youtube-transcriber-") as temp_dir:
            working_dir = Path(temp_dir)
            audio_path = download_audio(args.url, working_dir)
            segments = transcribe_audio(
                audio_path=audio_path,
                language=args.language,
                model=args.model,
                device=args.device,
            )
            if args.keep_audio:
                target = text_output.with_suffix(".mp3")
                ensure_parent(target)
                shutil.copy2(audio_path, target)

    write_outputs(
        segments=segments,
        text_output=text_output,
        json_output=json_output,
        srt_output=srt_output,
        with_timestamps=args.with_timestamps,
    )
    print(f"Wrote transcript to {text_output}")
    if json_output:
        print(f"Wrote JSON segments to {json_output}")
    if srt_output:
        print(f"Wrote SRT subtitles to {srt_output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)

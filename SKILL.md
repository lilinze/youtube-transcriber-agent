---
name: youtube-transcriber-agent
description: Convert YouTube videos into plain text transcripts. Use when Codex needs to transcribe a YouTube URL, extract subtitles or captions, fall back to speech-to-text when captions are unavailable, or produce timestamped transcript files from YouTube content.
---

# YouTube Transcriber Agent

Convert a YouTube video into text with the bundled script at `scripts/transcribe_youtube.py`.

## Workflow

1. Prefer fetching existing subtitles first.
2. Fall back to speech-to-text only when subtitles are unavailable or the user explicitly asks for a fresh transcription.
3. Write plain text output by default.
4. Keep timestamped segment output when the user needs subtitles, QA, or downstream chunking.
5. Prefer an isolated conda environment when the machine already uses Anaconda or Miniconda.

## Script

Run:

```powershell
.\install.ps1 -UseConda
.\run.ps1 "<youtube-url>" -Output out/transcript.txt
```

Fastest Windows entry:

```powershell
drop-run.cmd
```

You can double-click `drop-run.cmd` and paste a YouTube link, or drag a `.url` / `.txt` file containing the link onto it.

Desktop window entry:

```powershell
gui-run.cmd
```

Double-click `gui-run.cmd` to open a small local app for paste-and-run usage.

or:

```powershell
.\install.ps1
.\run.ps1 "<youtube-url>" -Output out/transcript.txt
```

Direct Python usage:

```powershell
python scripts/transcribe_youtube.py "<youtube-url>" --output out/transcript.txt
```

Useful flags:

- `--mode auto|subtitles|asr`: choose automatic mode, subtitles only, or forced speech-to-text.
- `--language <code>`: prefer a language such as `en`, `zh-Hans`, or `ja`.
- `--with-timestamps`: include `[start-end]` markers in text output.
- `--json-output <path>`: also emit structured segment data.
- `--srt-output <path>`: also emit `.srt` subtitles.
- `--model <name>`: choose a Whisper model such as `base`, `small`, or `medium`.
- `--keep-audio`: keep the downloaded audio file instead of deleting it.
- `run.ps1` defaults to the conda environment `youtube-transcriber-agent`; override with `-EnvName` only when needed.
- `drop-run.cmd` is a simplified launcher for day-to-day use on Windows and writes results into a timestamped folder under `out/`.
- `gui-run.cmd` opens a minimal desktop UI backed by `scripts/gui_launcher.py`.

## Dependencies

Install the tools that match the chosen path:

- Subtitle path: `youtube-transcript-api`
- ASR path: `yt-dlp`, `ffmpeg`, and either `faster-whisper` or `openai-whisper`
- Conda path: use `environment.yml` to create an isolated environment that already includes `ffmpeg`

If both ASR libraries are installed, prefer `faster-whisper`.

## Operational Notes

- Use `--mode subtitles` when the user wants the platform captions exactly as published.
- Use `--mode asr` when the user wants a fresh transcript even if captions exist.
- If subtitles are disabled, auto-generated subtitles are missing, or the video is long and uncaptioned, use ASR.
- For Chinese output, pass `--language zh` or a more specific tag if known.
- If the environment lacks `ffmpeg`, stop and surface that prerequisite instead of silently failing.

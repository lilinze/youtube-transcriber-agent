# YouTube Transcriber Agent

A local Windows-first tool for turning YouTube videos into text.

It supports:

- plain text transcript output
- `.srt` subtitle output
- `.json` segment output
- automatic fallback from YouTube subtitles to Whisper ASR
- a simple desktop GUI launcher
- a simple double-click / paste-link launcher

## Features

- Prefer published YouTube subtitles when available
- Fall back to `yt-dlp + faster-whisper` when subtitles are unavailable
- Run inside an isolated conda environment
- Support Chinese transcription with `-Language zh`
- Generate timestamped output folders for repeated runs

## Project Structure

- `run.ps1`: main command-line entry
- `install.ps1`: environment setup script
- `drop-run.cmd`: double-click and paste-link entry
- `gui-run.cmd`: desktop GUI entry
- `scripts/transcribe_youtube.py`: core transcription script
- `scripts/gui_launcher.py`: local GUI launcher
- `environment.yml`: conda environment definition

## Requirements

- Windows
- Anaconda or Miniconda
- PowerShell
- Internet access for YouTube download / subtitle retrieval

## Setup

Create the isolated conda environment:

```powershell
cd D:\project\codex
.\install.ps1 -UseConda
```

This installs:

- Python 3.11
- `ffmpeg`
- `youtube-transcript-api`
- `yt-dlp`
- `faster-whisper`

## Usage

### 1. GUI

Double-click:

```powershell
gui-run.cmd
```

Then:

1. Paste a YouTube link
2. Keep `Language` as `zh` for Chinese videos or change it
3. Click `Start`

The GUI will show logs and preview the generated transcript.

### 2. Simple launcher

Double-click:

```powershell
drop-run.cmd
```

Then paste a YouTube URL and press Enter.

You can also drag a `.txt` or `.url` file containing a YouTube link onto it.

### 3. Command line

Basic usage:

```powershell
.\run.ps1 "https://www.youtube.com/watch?v=VIDEO_ID" -Output out/transcript.txt
```

Recommended for Chinese videos:

```powershell
.\run.ps1 "https://www.youtube.com/watch?v=VIDEO_ID" -Language zh -Output out/transcript.txt -SrtOutput out/transcript.srt -JsonOutput out/transcript.json
```

## Common Options

- `-Mode auto`: prefer subtitles, then fall back to ASR
- `-Mode subtitles`: only fetch YouTube subtitles
- `-Mode asr`: force speech-to-text
- `-Language zh`: prefer Chinese recognition
- `-WithTimestamps`: include timestamps in text output
- `-KeepAudio`: keep downloaded audio

## Output

Outputs are written under `out/`.

Typical files:

- `transcript.txt`
- `transcript.srt`
- `transcript.json`

The simplified launchers create timestamped folders such as:

```text
out/run-20260228-131700/
```

## Notes

- For some videos, platform subtitles are unavailable, so the tool will use ASR instead.
- ASR may introduce errors in company names, tickers, or technical terms.
- On Windows, outputs are written as UTF-8 with BOM for better compatibility with common editors.

## GitHub

Repository:

- https://github.com/lilinze/youtube-transcriber-agent

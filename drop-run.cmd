@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "INPUT=%~1"
if "%INPUT%"=="" (
    set /p INPUT=Paste YouTube URL and press Enter: 
)

if "%INPUT%"=="" (
    echo No input provided.
    pause
    exit /b 1
)

set "URL=%INPUT%"

if exist "%INPUT%" (
    for %%I in ("%INPUT%") do (
        set "EXT=%%~xI"
    )

    if /I "!EXT!"==".url" (
        for /f "usebackq tokens=1,* delims==" %%A in ("%INPUT%") do (
            if /I "%%A"=="URL" set "URL=%%B"
        )
    ) else if /I "!EXT!"==".txt" (
        set /p URL=<"%INPUT%"
    )
)

if "%URL%"=="" (
    echo Failed to resolve a YouTube URL.
    pause
    exit /b 1
)

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format ''yyyyMMdd-HHmmss''"') do set "STAMP=%%I"
set "OUTDIR=out\run-%STAMP%"

echo Running transcription for:
echo %URL%
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0run.ps1" "%URL%" -Language zh -Output "%OUTDIR%\transcript.txt" -SrtOutput "%OUTDIR%\transcript.srt" -JsonOutput "%OUTDIR%\transcript.json"
if errorlevel 1 (
    echo.
    echo Transcription failed.
    pause
    exit /b 1
)

echo.
echo Done. Outputs:
echo %OUTDIR%\transcript.txt
echo %OUTDIR%\transcript.srt
echo %OUTDIR%\transcript.json
echo.
pause

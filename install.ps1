param(
    [switch]$UpgradePip,
    [switch]$UseConda,
    [string]$EnvName = "youtube-transcriber-agent"
)

$ErrorActionPreference = "Stop"

function Test-Command {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

if ($UseConda) {
    if (-not (Test-Command "conda")) {
        throw "Conda was not found on PATH."
    }

    Write-Host "Creating or updating conda environment '$EnvName'..."
    conda env update --name $EnvName --file environment.yml --prune

    Write-Host "Checking ffmpeg inside conda environment..."
    conda run -n $EnvName ffmpeg -version | Out-Null
    Write-Host "ffmpeg found in conda environment."

    Write-Host "Checking Python packages inside conda environment..."
    conda run -n $EnvName python -c "import importlib.util;mods=['youtube_transcript_api','yt_dlp','faster_whisper'];missing=[m for m in mods if importlib.util.find_spec(m) is None];print('Missing: ' + ', '.join(missing) if missing else 'All required Python packages are installed.')"
} else {
    Write-Host "Checking Python..."
    if (-not (Test-Command "python")) {
        throw "Python was not found on PATH."
    }

    if ($UpgradePip) {
        Write-Host "Upgrading pip..."
        python -m pip install --upgrade pip
    }

    Write-Host "Installing Python dependencies..."
    python -m pip install -r requirements.txt

    Write-Host "Checking ffmpeg..."
    if (Test-Command "ffmpeg") {
        Write-Host "ffmpeg found."
    } else {
        Write-Warning "ffmpeg was not found on PATH. Subtitle mode can still work, but ASR mode requires ffmpeg."
        Write-Host "Install ffmpeg and add it to PATH if you want speech-to-text fallback."
    }

    Write-Host "Checking optional runtime packages..."
    python -c "import importlib.util;mods=['youtube_transcript_api','yt_dlp','faster_whisper'];missing=[m for m in mods if importlib.util.find_spec(m) is None];print('Missing: ' + ', '.join(missing) if missing else 'All required Python packages are installed.')"
}

Write-Host "Setup complete."

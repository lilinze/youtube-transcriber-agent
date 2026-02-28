param(
    [Parameter(Mandatory = $true)]
    [string]$Url,

    [string]$Output = "out/transcript.txt",

    [string]$JsonOutput,

    [string]$SrtOutput,

    [ValidateSet("auto", "subtitles", "asr")]
    [string]$Mode = "auto",

    [string]$Language,

    [string]$Model = "base",

    [string]$EnvName = "youtube-transcriber-agent",

    [switch]$WithTimestamps,

    [switch]$KeepAudio
)

$argsList = @(
    "scripts/transcribe_youtube.py",
    $Url,
    "--output",
    $Output,
    "--mode",
    $Mode,
    "--model",
    $Model
)

if ($JsonOutput) {
    $argsList += @("--json-output", $JsonOutput)
}

if ($SrtOutput) {
    $argsList += @("--srt-output", $SrtOutput)
}

if ($Language) {
    $argsList += @("--language", $Language)
}

if ($WithTimestamps) {
    $argsList += "--with-timestamps"
}

if ($KeepAudio) {
    $argsList += "--keep-audio"
}

if ($EnvName) {
    conda run -n $EnvName python @argsList
} else {
    python @argsList
}

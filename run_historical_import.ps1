param(
    [Parameter(Mandatory = $true)]
    [string]$ZipPath,

    [string]$VaultPath = (Join-Path $HOME 'Vault'),

    [string]$Model = 'small'
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$zip = (Resolve-Path -LiteralPath $ZipPath).Path
$vault = [System.IO.Path]::GetFullPath($VaultPath)
$marker = Join-Path $vault '.historical_import.running'
$logDir = Join-Path $vault 'logs'
$logFile = Join-Path $logDir 'historical-import.log'

if (Test-Path -LiteralPath $marker) {
    throw "Un import historique est déjà en cours : $marker"
}

$pythonRoot = Join-Path $env:LOCALAPPDATA 'Programs\Python'
$pythonExe = Get-ChildItem -LiteralPath $pythonRoot -Filter python.exe -File -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch '\\Lib\\venv\\' } |
    Sort-Object FullName -Descending |
    Select-Object -First 1 -ExpandProperty FullName
if (-not $pythonExe) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) { $pythonExe = $pythonCommand.Source }
}
if (-not $pythonExe) {
    throw 'Python est introuvable. Lance setup_windows.ps1.'
}

$ffmpegCommand = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpegCommand) {
    $wingetPackages = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
    $ffmpegExe = Get-ChildItem -LiteralPath $wingetPackages -Filter ffmpeg.exe -File -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName
    if ($ffmpegExe) {
        $env:Path = "$(Split-Path -Parent $ffmpegExe);$env:Path"
    }
}

New-Item -ItemType Directory -Force -Path $vault, $logDir | Out-Null
New-Item -ItemType File -Path $marker | Out-Null

try {
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $env:PYTHONIOENCODING = 'utf-8'
    $OutputEncoding = [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
    Add-Content -LiteralPath $logFile -Value "`n=== Import historique $timestamp ===" -Encoding UTF8
    $output = & $pythonExe (Join-Path $repo 'vault.py') import $zip --vault $vault --cookies firefox --model $Model 2>&1 | Out-String
    $exitCode = $LASTEXITCODE
    Add-Content -LiteralPath $logFile -Value $output -Encoding UTF8
    exit $exitCode
}
finally {
    Remove-Item -LiteralPath $marker -Force -ErrorAction SilentlyContinue
}

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

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    throw 'Python est introuvable. Lance setup_windows.ps1.'
}

New-Item -ItemType Directory -Force -Path $vault, $logDir | Out-Null
New-Item -ItemType File -Path $marker | Out-Null

try {
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content -LiteralPath $logFile -Value "`n=== Import historique $timestamp ===" -Encoding UTF8
    & $pythonCommand.Source (Join-Path $repo 'vault.py') import $zip --vault $vault --cookies firefox --model $Model *>> $logFile
    exit $LASTEXITCODE
}
finally {
    Remove-Item -LiteralPath $marker -Force -ErrorAction SilentlyContinue
}

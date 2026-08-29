$ErrorActionPreference = 'Stop'
Write-Host '=== Reels Vault - installation Windows ==='

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host 'Python absent. Installation via winget...'
    winget install --id Python.Python.3.12 -e
    Write-Host 'Ferme puis relance PowerShell, puis relance ce script.'
    exit 0
}

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host 'FFmpeg absent. Installation via winget...'
    winget install --id Gyan.FFmpeg -e
    Write-Host 'FFmpeg vient d être installé. Si la commande reste introuvable, ferme puis relance PowerShell.'
}

$vault = Join-Path $HOME 'Vault'
New-Item -ItemType Directory -Force -Path $vault | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $vault 'raw') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $vault 'images') | Out-Null

Write-Host ''
Write-Host 'Installation terminée.'
Write-Host "Dossier Vault : $vault"
Write-Host 'Prochaine étape : importer ton ZIP Instagram puis tester 5 à 10 Reels.'

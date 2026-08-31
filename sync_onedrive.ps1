param(
    [string]$VaultPath = (Join-Path $HOME 'Vault'),
    [string]$OneDriveFolder = ''
)

$ErrorActionPreference = 'Stop'

function Resolve-OneDriveRoot {
    param([string]$Explicit)
    if ($Explicit) { return $Explicit }
    foreach ($candidate in @($env:OneDrive, $env:OneDriveConsumer, $env:OneDriveCommercial)) {
        if ($candidate -and (Test-Path $candidate)) { return $candidate }
    }
    throw 'Dossier OneDrive introuvable. Lance OneDrive sur Windows ou utilise -OneDriveFolder "C:\chemin\OneDrive".'
}

$root = Resolve-OneDriveRoot $OneDriveFolder
$dest = Join-Path $root 'Reels Vault'
New-Item -ItemType Directory -Force -Path $dest | Out-Null

$source = Join-Path $VaultPath 'Vault Instagram.md'
if (-not (Test-Path $source)) {
    throw "Index introuvable : $source. Lance d'abord : python vault.py rebuild"
}

Copy-Item -Force $source (Join-Path $dest 'Vault Instagram.md')

$json = Join-Path $VaultPath 'vault_data.json'
if (Test-Path $json) {
    Copy-Item -Force $json (Join-Path $dest 'vault_data.json')
}

Write-Host 'Synchronisation OneDrive terminée.'
Write-Host "Dossier : $dest"
Write-Host "Fichier ChatGPT : $(Join-Path $dest 'Vault Instagram.md')"

param(
    [Parameter(Mandatory = $true)]
    [string]$VaultPath,

    [Parameter(Mandatory = $true)]
    [string]$IndexRepo
)

$ErrorActionPreference = 'Stop'

$vault = (Resolve-Path -LiteralPath $VaultPath).Path
$repo = (Resolve-Path -LiteralPath $IndexRepo).Path
$sourceMd = Join-Path $vault 'Vault Instagram.md'
$sourceJson = Join-Path $vault 'vault_data.json'
$sourceSearch = Join-Path $vault 'vault_search'

foreach ($source in @($sourceMd, $sourceJson)) {
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Index introuvable : $source"
    }
}
if (-not (Test-Path -LiteralPath (Join-Path $sourceSearch 'manifest.json'))) {
    throw "Index de recherche introuvable : $sourceSearch"
}
if (-not (Test-Path -LiteralPath (Join-Path $repo '.git'))) {
    throw "Le dossier n'est pas un dépôt Git : $repo"
}

Push-Location $repo
try {
    git rev-parse --is-inside-work-tree | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Dépôt Git invalide : $repo" }

    Copy-Item -LiteralPath $sourceMd -Destination (Join-Path $repo 'Vault Instagram.md') -Force
    Copy-Item -LiteralPath $sourceJson -Destination (Join-Path $repo 'vault_data.json') -Force
    $destSearch = Join-Path $repo 'vault_search'
    New-Item -ItemType Directory -Force -Path $destSearch | Out-Null
    Copy-Item -Path (Join-Path $sourceSearch '*') -Destination $destSearch -Force

    git add -- 'Vault Instagram.md' 'vault_data.json' 'vault_search'
    if ($LASTEXITCODE -ne 0) { throw 'Impossible de préparer les index GitHub.' }

    git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host 'GitHub privé déjà à jour.'
        exit 0
    }
    if ($LASTEXITCODE -ne 1) { throw 'Impossible de vérifier les changements GitHub.' }

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    git commit -m "Update Reels Vault index $timestamp"
    if ($LASTEXITCODE -ne 0) { throw 'Commit GitHub impossible.' }

    git push origin HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Push GitHub impossible.' }

    Write-Host 'Index GitHub privé publié.'
}
finally {
    Pop-Location
}

param(
    [string]$InboxPath = '',
    [switch]$InstallAutomation,
    [int]$IntervalMinutes = 30,
    [string]$IndexRepo = ''
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repo

Write-Host '=== Reels Vault - préparation automatique Windows ==='

& (Join-Path $repo 'setup_windows.ps1')

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host ''
    Write-Host 'Python vient probablement d être installé.'
    Write-Host 'Ferme puis rouvre PowerShell et relance exactement la même commande.'
    exit 0
}

if (-not $InboxPath) {
    $candidates = @(
        (Join-Path $HOME 'Dropbox\Reels Vault\Inbox\inbox.txt'),
        (Join-Path $HOME 'Dropbox\Reel Vault\Inbox\inbox.txt'),
        (Join-Path $HOME 'Dropbox (Personal)\Reels Vault\Inbox\inbox.txt'),
        (Join-Path $HOME 'Dropbox (Personal)\Reel Vault\Inbox\inbox.txt')
    )
    $InboxPath = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}

if (-not $InboxPath) {
    Write-Host ''
    Write-Host 'Inbox Dropbox non trouvée automatiquement.'
    Write-Host 'Repère inbox.txt dans Dropbox puis relance :'
    Write-Host '.\bootstrap_windows.ps1 -InboxPath "C:\chemin\Dropbox\Reels Vault\Inbox\inbox.txt"'
    exit 1
}

$InboxPath = (Resolve-Path -LiteralPath $InboxPath).Path
Write-Host "Inbox détectée : $InboxPath"
[Environment]::SetEnvironmentVariable('VAULT_INBOX', $InboxPath, 'User')
$env:VAULT_INBOX = $InboxPath

Write-Host ''
Write-Host '=== Test gratuit / hors réseau ==='
python vault.py test
if ($LASTEXITCODE -ne 0) { throw 'Le smoke test a échoué.' }

Write-Host ''
Write-Host '=== Diagnostic ==='
python vault.py doctor --inbox "$InboxPath"
$doctorExit = $LASTEXITCODE
if ($doctorExit -eq 2) {
    Write-Host 'Diagnostic : au moins un FAIL. Ne lance pas encore d import réel.'
    exit 2
}
if ($doctorExit -eq 1) {
    Write-Host 'Diagnostic : seulement des avertissements. Lis les WARN avant le test réel.'
}

if ($InstallAutomation) {
    Write-Host ''
    Write-Host '=== Installation de la tâche automatique ==='
    & (Join-Path $repo 'install_windows_automation.ps1') -InboxPath $InboxPath -IntervalMinutes $IntervalMinutes -IndexRepo $IndexRepo
} else {
    Write-Host ''
    Write-Host 'Préparation terminée.'
    Write-Host 'Prochaine étape recommandée : test réel de 5 liens seulement.'
    Write-Host "python vault.py inbox --file `"$InboxPath`" --limit 5 --clear"
    Write-Host ''
    Write-Host 'N installe la tâche permanente qu après validation de ce test.'
}

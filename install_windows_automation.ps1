param(
    [Parameter(Mandatory = $true)]
    [string]$InboxPath,

    [int]$IntervalMinutes = 30,

    [string]$TaskName = 'Reels Vault Inbox',

    [string]$VaultPath = (Join-Path $HOME 'Vault'),

    [string]$IndexRepo = ''
)

$ErrorActionPreference = 'Stop'

Write-Host '=== Reels Vault - automatisation Windows ==='

if ($IntervalMinutes -lt 5) {
    throw 'IntervalMinutes doit être au minimum de 5 minutes.'
}

$inbox = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $InboxPath).Path)
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$vaultPy = Join-Path $repo 'vault.py'

if (-not (Test-Path -LiteralPath $vaultPy)) {
    throw "vault.py introuvable dans $repo"
}

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    throw 'Python est introuvable. Lance d abord setup_windows.ps1.'
}
$pythonExe = $pythonCommand.Source

New-Item -ItemType Directory -Force -Path $VaultPath | Out-Null
$logDir = Join-Path $VaultPath 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# Sauvegarde le chemin de l inbox pour les lancements manuels futurs.
[Environment]::SetEnvironmentVariable('VAULT_INBOX', $inbox, 'User')
$env:VAULT_INBOX = $inbox

if ($IndexRepo) {
    $indexRepoPath = (Resolve-Path -LiteralPath $IndexRepo).Path
    if (-not (Test-Path -LiteralPath (Join-Path $indexRepoPath '.git'))) {
        throw "IndexRepo n'est pas un dépôt Git : $indexRepoPath"
    }
    [Environment]::SetEnvironmentVariable('VAULT_INDEX_REPO', $indexRepoPath, 'User')
    $env:VAULT_INDEX_REPO = $indexRepoPath
    $indexRepoLine = "`$env:VAULT_INDEX_REPO = '$indexRepoPath'"
} else {
    $indexRepoLine = ''
}

$runner = Join-Path $VaultPath 'run_inbox.ps1'
$logFile = Join-Path $logDir 'inbox-task.log'

$runnerContent = @"
`$ErrorActionPreference = 'Continue'
`$env:PYTHONIOENCODING = 'utf-8'
`$OutputEncoding = [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
$indexRepoLine
`$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Add-Content -LiteralPath '$logFile' -Value "`n=== `$timestamp ===" -Encoding UTF8
if (Test-Path -LiteralPath '$VaultPath\.historical_import.running') {
    Add-Content -LiteralPath '$logFile' -Value 'Import historique actif : inbox reportée au prochain passage.' -Encoding UTF8
    exit 0
}
`$output = & '$pythonExe' '$vaultPy' inbox --file '$inbox' --vault '$VaultPath' --cookies firefox --clear 2>&1 | Out-String
`$exitCode = `$LASTEXITCODE
Add-Content -LiteralPath '$logFile' -Value `$output -Encoding UTF8
exit `$exitCode
"@
Set-Content -LiteralPath $runner -Value $runnerContent -Encoding UTF8

$action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runner`""

$start = (Get-Date).AddMinutes(1)
$duration = New-TimeSpan -Days 3650
$interval = New-TimeSpan -Minutes $IntervalMinutes
$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At $start `
    -RepetitionInterval $interval `
    -RepetitionDuration $duration

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description 'Traite automatiquement les liens envoyés depuis l iPhone vers Reels Vault.' `
    -Force | Out-Null

Write-Host ''
Write-Host 'Automatisation installée.'
Write-Host "Tâche : $TaskName"
Write-Host "Inbox : $inbox"
Write-Host "Intervalle : toutes les $IntervalMinutes minutes"
Write-Host "Vault : $VaultPath"
Write-Host "Logs : $logFile"
Write-Host ''
Write-Host 'Le premier lancement automatique aura lieu dans environ 1 minute.'
Write-Host "Test manuel : Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Suppression : Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"

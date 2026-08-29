param(
    [Parameter(Mandatory = $true)]
    [string]$InboxPath,

    [int]$IntervalMinutes = 30,

    [string]$TaskName = 'Reels Vault Inbox',

    [string]$VaultPath = (Join-Path $HOME 'Vault')
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

$runner = Join-Path $VaultPath 'run_inbox.ps1'
$logFile = Join-Path $logDir 'inbox-task.log'

$runnerContent = @"
`$ErrorActionPreference = 'Continue'
`$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Add-Content -LiteralPath '$logFile' -Value "`n=== `$timestamp ==="
& '$pythonExe' '$vaultPy' inbox --file '$inbox' --vault '$VaultPath' --cookies firefox --clear *>> '$logFile'
exit `$LASTEXITCODE
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

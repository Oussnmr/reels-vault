param(
    [string]$VaultPath = (Join-Path $HOME 'Vault'),
    [string]$InboxPath = ''
)

$ErrorActionPreference = 'Continue'
$ok = 0
$warn = 0
$fail = 0

function Pass($msg) { $script:ok++; Write-Host "[OK]   $msg" }
function Warn($msg) { $script:warn++; Write-Host "[WARN] $msg" }
function Fail($msg) { $script:fail++; Write-Host "[FAIL] $msg" }

Write-Host '=== Reels Vault - diagnostic ==='
Write-Host "Vault : $VaultPath"
Write-Host ''

# Python
if (Get-Command python -ErrorAction SilentlyContinue) {
    try {
        $py = python --version 2>&1
        Pass "Python disponible ($py)"
    } catch { Fail 'Python est présent mais ne répond pas correctement.' }
} else { Fail 'Python introuvable.' }

# Modules Python
foreach ($module in @('yt_dlp','gallery_dl','faster_whisper')) {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        python -c "import $module" 2>$null
        if ($LASTEXITCODE -eq 0) { Pass "Module Python $module installé" } else { Fail "Module Python $module manquant" }
    }
}

# FFmpeg
if (Get-Command ffmpeg -ErrorAction SilentlyContinue) { Pass 'FFmpeg disponible' } else { Fail 'FFmpeg introuvable' }

# Firefox
$firefoxCandidates = @(
    "$env:ProgramFiles\Mozilla Firefox\firefox.exe",
    "$env:ProgramFiles(x86)\Mozilla Firefox\firefox.exe"
)
$firefox = $firefoxCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if ($firefox) { Pass "Firefox détecté ($firefox)" } else { Warn 'Firefox non détecté. Les cookies Instagram devront être fournis autrement.' }

# Vault folders
if (Test-Path $VaultPath) { Pass 'Dossier Vault présent' } else { Warn 'Dossier Vault absent (il sera créé au premier lancement)' }
foreach ($sub in @('raw','images')) {
    $p = Join-Path $VaultPath $sub
    if (Test-Path $p) { Pass "Sous-dossier $sub présent" } else { Warn "Sous-dossier $sub absent" }
}

# OneDrive
$oneDriveRoot = @($env:OneDrive, $env:OneDriveConsumer, $env:OneDriveCommercial) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if ($oneDriveRoot) {
    Pass "OneDrive détecté ($oneDriveRoot)"
    $syncDir = Join-Path $oneDriveRoot 'Reels Vault'
    if (Test-Path $syncDir) { Pass 'Dossier OneDrive/Reels Vault présent' } else { Warn 'Dossier OneDrive/Reels Vault pas encore créé' }
} else { Warn 'OneDrive Windows non détecté ou non connecté' }

# Inbox
if (-not $InboxPath) { $InboxPath = [Environment]::GetEnvironmentVariable('VAULT_INBOX', 'User') }
if ($InboxPath) {
    if (Test-Path $InboxPath) {
        Pass "Inbox trouvée ($InboxPath)"
        try {
            $content = Get-Content -Raw -ErrorAction Stop $InboxPath
            $count = ($content -split "`r?`n" | Where-Object { $_.Trim() }).Count
            Pass "Inbox lisible ($count lien(s) en attente)"
        } catch { Fail 'Inbox trouvée mais illisible' }
    } else { Fail "VAULT_INBOX configuré mais fichier introuvable ($InboxPath)" }
} else { Warn 'Inbox iPhone non configurée (VAULT_INBOX absent)' }

# Scheduled task
try {
    $task = Get-ScheduledTask -TaskName 'Reels Vault Inbox' -ErrorAction SilentlyContinue
    if ($task) {
        Pass "Tâche planifiée présente (état: $($task.State))"
    } else { Warn 'Tâche planifiée Reels Vault Inbox absente' }
} catch { Warn 'Impossible de lire le Planificateur de tâches' }

# Generated files
foreach ($file in @('Vault Instagram.md','vault_data.json','vault.html')) {
    $p = Join-Path $VaultPath $file
    if (Test-Path $p) { Pass "$file présent" } else { Warn "$file pas encore généré" }
}

Write-Host ''
Write-Host "Résultat : $ok OK, $warn avertissement(s), $fail erreur(s)."
if ($fail -gt 0) {
    Write-Host 'Le système n’est pas prêt. Corrige les éléments [FAIL] avant un import complet.'
    exit 2
}
if ($warn -gt 0) {
    Write-Host 'Le socle fonctionne, mais certaines fonctions ne sont pas encore configurées.'
    exit 1
}
Write-Host 'Tout est prêt pour un test de 5 à 10 Reels.'
exit 0

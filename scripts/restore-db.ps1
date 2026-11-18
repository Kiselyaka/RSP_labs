param(
    [Parameter(Mandatory=$true)][string]$BackupFile,
    [string]$Project = 'rsp-lab6-demo'
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$resolvedBackup = (Resolve-Path -LiteralPath $BackupFile).Path
if (Test-Path -LiteralPath ($resolvedBackup + '.sha256')) {
    $expectedHash = [IO.File]::ReadAllText($resolvedBackup + '.sha256').Trim()
    if ((Get-FileHash -LiteralPath $resolvedBackup -Algorithm SHA256).Hash -ne $expectedHash) {
        throw 'Backup checksum mismatch. Restoration was cancelled.'
    }
}
Push-Location -LiteralPath $repoRoot
try {
    $dbId = docker compose -p $Project ps -q db
    if ($LASTEXITCODE -ne 0 -or -not $dbId) { throw 'Start the database before restoring a backup.' }
    $dbUser = docker exec $dbId printenv POSTGRES_USER
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read the database user.' }
    $dbName = docker exec $dbId printenv POSTGRES_DB
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read the database name.' }
    $containerFile = '/tmp/restore-' + [guid]::NewGuid().ToString('N') + '.dump'
    docker cp $resolvedBackup "${dbId}:$containerFile"
    if ($LASTEXITCODE -ne 0) { throw 'Cannot copy the backup into the container.' }
    docker exec $dbId pg_restore --list $containerFile | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Invalid backup archive.' }
    $appId = docker compose -p $Project ps -q app
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect the application.' }
    $wasRunning = [bool]$appId
    if ($wasRunning) {
        docker compose -p $Project stop app
        if ($LASTEXITCODE -ne 0) { throw 'Cannot stop the application.' }
    }
    try {
        Write-Output "Restoring $dbName in Compose project $Project from $resolvedBackup"
        docker exec -e 'PGOPTIONS=-c lock_timeout=5000' $dbId pg_restore -U $dbUser -d $dbName --clean --if-exists --no-owner --no-privileges --exit-on-error --single-transaction $containerFile
        if ($LASTEXITCODE -ne 0) { throw 'Restoration failed and its transaction was rolled back. Check open DBeaver transactions and the error above.' }
        Write-Output 'Schema and data restored successfully.'
    } finally {
        if ($wasRunning) {
            docker compose -p $Project start app
            if ($LASTEXITCODE -ne 0) { Write-Warning 'Start the application manually after checking its logs.' }
        }
    }
} finally {
    Pop-Location
}

param([string]$Project = 'rsp-lab6-demo')
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $repoRoot
try {
    $dbId = docker compose -p $Project ps -q db
    if ($LASTEXITCODE -ne 0 -or -not $dbId) { throw 'Start the database before creating a backup.' }
    $dbUser = docker exec $dbId printenv POSTGRES_USER
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read the database user.' }
    $dbName = docker exec $dbId printenv POSTGRES_DB
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read the database name.' }
    $backupDirectory = Join-Path $repoRoot 'backups'
    New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null
    $backupName = '{0}-{1}-{2}.dump' -f $dbName, (Get-Date -Format 'yyyyMMdd-HHmmss'), ([guid]::NewGuid().ToString('N').Substring(0,6))
    $backupFile = Join-Path $backupDirectory $backupName
    $containerFile = '/tmp/' + $backupName
    docker exec $dbId pg_dump -U $dbUser -d $dbName --format=custom --no-owner --no-privileges --file=$containerFile
    if ($LASTEXITCODE -ne 0) { throw 'pg_dump failed.' }
    docker exec $dbId pg_restore --list $containerFile | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'The backup archive could not be read.' }
    docker cp "${dbId}:$containerFile" $backupFile
    if ($LASTEXITCODE -ne 0) { throw 'Could not copy the backup to Windows.' }
    $sha256 = [Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($backupFile)
    try {
        $checksum = [BitConverter]::ToString($sha256.ComputeHash($stream)).Replace('-', '')
    } finally {
        $stream.Dispose()
        $sha256.Dispose()
    }
    [IO.File]::WriteAllText($backupFile + '.sha256', $checksum, [Text.Encoding]::ASCII)
    Write-Output "Backup saved: $backupFile"
    Write-Output "SHA256: $checksum"
    Write-Output 'The archive contains the schema, all table data and the migration version.'
} finally {
    Pop-Location
}

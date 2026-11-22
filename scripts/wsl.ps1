# Run a repo script inside the WSL distro from Windows PowerShell.
#   .\scripts\wsl.ps1 status
#   .\scripts\wsl.ps1 serve
#   .\scripts\wsl.ps1 h3gen example distracted-boyfriend
#   .\scripts\wsl.ps1 h3gen generate --first C:\path\img.png --prompt-file C:\path\prompt.txt
# Windows paths (C:\...) in the arguments are converted to /mnt/c/... automatically.
# Distro: $env:H3_WSL_DISTRO, else H3_WSL_DISTRO in config/h3gen.env, else the WSL default distro.
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Command,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest
)
$ErrorActionPreference = 'Stop'
$repoWin = Split-Path -Parent $PSScriptRoot
$distro = $env:H3_WSL_DISTRO
$envFile = Join-Path $repoWin 'config\h3gen.env'
if (-not $distro -and (Test-Path $envFile)) {
    foreach ($line in Get-Content $envFile) {
        if ($line -match '^\s*H3_WSL_DISTRO=["'']?([^"''#\s]*)') { $distro = $Matches[1] }
    }
}
$wslArgs = if ($distro) { @('-d', $distro) } else { @() }

function ConvertTo-WslPath([string]$p) {
    if ($p -match '^([A-Za-z]):[\\/](.*)$') {
        return '/mnt/' + $Matches[1].ToLower() + '/' + ($Matches[2] -replace '\\', '/')
    }
    return $p
}
function ConvertTo-BashQuoted([string]$s) { return "'" + ($s -replace "'", "'\''") + "'" }

$repo = ConvertTo-WslPath $repoWin
$script = switch ($Command) {
    'h3gen' { 'scripts/h3gen' }
    default { "bash scripts/$Command.sh" }
}
# Guard the empty case: piping $null into ForEach-Object runs once and would pass an empty '' argument.
$argsQuoted = if ($Rest) { ($Rest | ForEach-Object { ConvertTo-BashQuoted (ConvertTo-WslPath $_) }) -join ' ' } else { '' }
# Progress goes to stderr. With 'Stop', Windows PowerShell 5.1 turns the first redirected stderr line
# (2>&1, *> file) into a terminating error and kills the run, so relax it for the native call.
$ErrorActionPreference = 'Continue'
wsl @wslArgs -- bash -lc "cd $(ConvertTo-BashQuoted $repo) && $script $argsQuoted"
exit $LASTEXITCODE

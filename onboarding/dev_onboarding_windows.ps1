#!/usr/bin/env pwsh
#Requires -Version 7.0

[CmdletBinding()]
param(
    [switch]$All,
    [switch]$Core,
    [string]$Steps = "",
    [switch]$Yes,
    [switch]$Plan,
    [switch]$DryRun,
    [switch]$NoColor,
    [string]$RepoRoot = "",
    [string]$GitHubRoot = "",
    [string]$HaConfigDir = "",
    [string]$HaComposeFile = "",
    [string]$MaDataDir = "",
    [string]$HaHostUrl = "",
    [string]$MaHostUrl = "",
    [string]$NgrokDomain = "",
    [switch]$PromptSecrets,
    [switch]$RunCiPush,
    [string]$CiBranch = "",
    [string]$E2EVersion = "3.1.999",
    [string]$EnvFile = "",
    [string]$LogFile = "",
    [switch]$NoLogFile,
    [switch]$Library,
    [switch]$Help
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-IsAdministrator {
    if (-not $IsWindows) {
        return $false
    }
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not $Library -and (Test-IsAdministrator)) {
    throw "Do not run this onboarding script as Administrator. Open a normal PowerShell terminal as your current user and run it again."
}

$Script:ScriptName = Split-Path -Leaf $PSCommandPath
$Script:ScriptRoot = Split-Path -Parent $PSCommandPath
if (-not $RepoRoot) {
    $defaultWindowsRepoRoot = Join-Path $HOME "LocalDocuments\GitHub\djconnect"
    $repoCandidates = @(
        (Join-Path $HOME "LocalDocuments\GitHub\djconnect"),
        (Get-Location).Path
    )
    foreach ($candidate in $repoCandidates) {
        $integrationDir = Join-Path $candidate "custom_components\djconnect"
        if (Test-Path $integrationDir) {
            $RepoRoot = (Resolve-Path $candidate).Path
            break
        }
    }
    if (-not $RepoRoot) {
        $RepoRoot = $defaultWindowsRepoRoot
    }
}
if (-not $GitHubRoot) {
    $GitHubRoot = if ($RepoRoot -like "C:\Mac\Home\*") { Join-Path $HOME "Documents\GitHub" } else { Split-Path -Parent $RepoRoot }
    if (-not $GitHubRoot -or $GitHubRoot -ieq "C:\Users") {
        $GitHubRoot = Join-Path $HOME "LocalDocuments\GitHub"
    }
}
if ($GitHubRoot -like "C:\Mac\Home\*") {
    $GitHubRoot = Join-Path $HOME "LocalDocuments\GitHub"
}
if ($RepoRoot -like "C:\Mac\Home\*") {
    $localRepoRoot = Join-Path $GitHubRoot "djconnect"
    if (Test-Path (Join-Path $localRepoRoot "custom_components\djconnect")) {
        $RepoRoot = $localRepoRoot
    }
}
if (-not $HaConfigDir) {
    $HaConfigDir = if ($env:HA_CONFIG_DIR) { $env:HA_CONFIG_DIR } else { Join-Path $HOME "docker\homeassistant\config" }
}
if (-not $HaComposeFile) {
    $HaComposeFile = if ($env:HA_COMPOSE_FILE) { $env:HA_COMPOSE_FILE } else { Join-Path (Split-Path -Parent $HaConfigDir) "docker-compose.yml" }
}
if (-not $MaDataDir) {
    $MaDataDir = if ($env:MA_DATA_DIR) { $env:MA_DATA_DIR } else { Join-Path $HOME "docker\music-assistant-server\data" }
}
if (-not $HaHostUrl) {
    $HaHostUrl = if ($env:HA_HOST_URL) { $env:HA_HOST_URL } else { "http://10.211.55.2:8123" }
}
if (-not $MaHostUrl) {
    $MaHostUrl = if ($env:MA_HOST_URL) { $env:MA_HOST_URL } else { "http://10.211.55.2:8095" }
}
if (-not $NgrokDomain -and $env:NGROK_DOMAIN) {
    $NgrokDomain = $env:NGROK_DOMAIN
}
if (-not $CiBranch) {
    $CiBranch = if ($env:CI_BRANCH) { $env:CI_BRANCH } else { "codex/onboarding-ci-smoke-$(Get-Date -Format yyyyMMdd-HHmmss)" }
}
if (-not $EnvFile) {
    $EnvFile = if ($env:ONBOARDING_ENV_FILE) { $env:ONBOARDING_ENV_FILE } else { Join-Path $RepoRoot ".djconnect-onboarding.env" }
}
if (-not $LogFile -and -not $NoLogFile) {
    $logDir = if ($env:LOG_DIR) { $env:LOG_DIR } else { Join-Path $RepoRoot "logs" }
    $LogFile = Join-Path $logDir "dev_onboarding_windows_$(Get-Date -Format yyyyMMdd_HHmmss).log"
}

$Script:StepCatalog = [ordered]@{
    0  = "Preflight"
    1  = "Install Windows package manager tooling"
    2  = "Install GitHub, Python, Node.js and .NET tooling"
    3  = "Clone or update DJConnect repositories"
    4  = "Prepare Python test environment"
    5  = "Run Home Assistant integration tests"
    6  = "Install .NET MAUI workloads for Windows client"
    7  = "Run Windows client validation"
    8  = "Check Home Assistant on macOS host"
    9  = "Sync DJConnect integration into Home Assistant config"
    10 = "Install HACS in local Home Assistant config"
    11 = "Check voice/backend services on macOS host"
    12 = "Install/start persistent ngrok tunnel for local Home Assistant"
    13 = "Local E2E release/build smoke checks"
    14 = "CI smoke push"
}

$Script:UseColor = -not $NoColor -and -not $env:NO_COLOR

function Write-Styled {
    param(
        [Parameter(Mandatory)][string]$Text,
        [ConsoleColor]$ForegroundColor = [ConsoleColor]::Gray,
        [switch]$NoNewline
    )
    if ($Script:UseColor) {
        Write-Host $Text -ForegroundColor $ForegroundColor -NoNewline:$NoNewline
    }
    else {
        Write-Host $Text -NoNewline:$NoNewline
    }
}

function Write-StatusLine {
    param(
        [Parameter(Mandatory)][string]$Label,
        [Parameter(Mandatory)][string]$Message,
        [Parameter(Mandatory)][ConsoleColor]$Color
    )
    Write-Styled ("{0,-5}" -f $Label) -ForegroundColor $Color -NoNewline
    Write-Styled $Message
}

function Write-Usage {
    @"
Usage: .\tools\$Script:ScriptName [options]

Automates DJConnect developer onboarding on a Windows 11 development machine.

Options:
  -All                  Run all steps.
  -Core                 Run core Home Assistant integration steps, 0-5 and 8-11.
  -Steps 1,2,5          Run selected numbered steps.
                        Omit -All/-Core/-Steps to open an interactive step menu.
  -Yes                  Use defaults and skip confirmation prompts.
  -Plan                 Print selected steps and exit without changes.
  -DryRun               Print mutating commands instead of executing them.
  -NoColor              Disable styled terminal output.
  -RepoRoot DIR         DJConnect Home Assistant integration repo root.
  -GitHubRoot DIR       Parent directory containing DJConnect sibling repos.
  -HaConfigDir DIR      Home Assistant config directory.
                        Default: $HaConfigDir
  -HaComposeFile FILE   Docker Compose file for local HA stack.
                        Default: $HaComposeFile
  -MaDataDir DIR        Music Assistant server data directory.
                        Default: $MaDataDir
  -HaHostUrl URL        Home Assistant URL exposed by the macOS host.
                        Default: $HaHostUrl
  -MaHostUrl URL        Music Assistant URL exposed by the macOS host.
                        Default: $MaHostUrl
  -NgrokDomain DOMAIN   Reserved ngrok static domain for stable external URL.
  -PromptSecrets        Prompt for optional local tokens before steps.
  -RunCiPush            Allow step 14 to push a CI smoke-test commit.
  -CiBranch BRANCH      Branch name for step 14.
  -E2EVersion VER       Version passed to release dry-run scripts.
                        Default: $E2EVersion
  -EnvFile FILE         Local onboarding env file for optional tokens.
                        Default: $EnvFile
  -LogFile FILE         Write a persistent run log.
  -NoLogFile            Disable persistent run logging.
  -Help                 Show this help.

Environment overrides:
  HA_CONFIG_DIR, HA_COMPOSE_FILE, MA_DATA_DIR, HA_HOST_URL, MA_HOST_URL, NGROK_DOMAIN,
  NGROK_AUTHTOKEN, ONBOARDING_ENV_FILE, LOG_DIR, CI_BRANCH,
  DJCONNECT_HA_WS_URL, DJCONNECT_HA_TOKEN
"@
    Write-StepMenu
}

function Write-StepMenu {
    Write-Host ""
    Write-Styled "Available steps:" -ForegroundColor Cyan
    foreach ($entry in $Script:StepCatalog.GetEnumerator()) {
        "{0,3}. {1}" -f $entry.Key, $entry.Value | Write-Host
    }
    Write-Host ""
    Write-Styled "Examples:" -ForegroundColor Cyan
    Write-Host "  .\tools\$Script:ScriptName -Core -Plan"
    Write-Host "  .\tools\$Script:ScriptName -Steps 0,1,2,3,4,5,8,9,10,11 -Yes"
    Write-Host "  .\tools\$Script:ScriptName -Steps 8,9,11 -DryRun -Yes"
    Write-Host "  .\tools\$Script:ScriptName -Steps 12 -NgrokDomain your-domain.ngrok-free.app -DryRun -Yes"
}

function Resolve-StepSelection([string]$Selection) {
    $value = $Selection.Trim().ToLowerInvariant()
    if (-not $value) {
        return @()
    }
    if ($value -in @("q", "quit", "exit")) {
        return $null
    }
    if ($value -eq "all") {
        return @($Script:StepCatalog.Keys)
    }
    if ($value -eq "core") {
        return @(0, 1, 2, 3, 4, 5, 8, 9, 10, 11)
    }
    return @($value.Split(",") | ForEach-Object {
        $part = $_.Trim()
        if (-not ($part -match "^\d+$")) {
            throw "Invalid step: $part"
        }
        [int]$part
    })
}

function Invoke-Steps {
    param(
        [Parameter(Mandatory)][int[]]$SelectedSteps,
        [switch]$SkipConfirmation
    )
    foreach ($step in $SelectedSteps) {
        if (-not $Script:StepCatalog.Contains($step)) {
            throw "Unknown step: $step"
        }
        if ($SkipConfirmation -or (Confirm-Step "Run step $step. $($Script:StepCatalog[$step])?")) {
            Invoke-StepByNumber $step
        }
    }
}

function Invoke-InteractiveMenu {
    Write-Usage
    while ($true) {
        $selection = Read-Host "Choose a step number, comma-separated steps, core/all, or q to quit"
        $resolved = Resolve-StepSelection $selection
        if ($null -eq $resolved) {
            Write-Host "Exiting onboarding menu."
            return
        }
        $selected = @($resolved)
        if ($selected.Count -eq 0) {
            Write-Host "No step selected. Enter q to quit."
            continue
        }
        Invoke-Steps -SelectedSteps $selected -SkipConfirmation
        Write-StepMenu
    }
}

function Write-Info([string]$Message) {
    Write-Host ""
    Write-Styled "==> " -ForegroundColor Cyan -NoNewline
    Write-Styled $Message
}

function Write-Ok([string]$Message) {
    Write-StatusLine -Label "[OK]" -Message $Message -Color Green
}

function Write-StatusOk([string]$Message) {
    Write-StatusLine -Label "OK" -Message $Message -Color Green
}

function Write-StatusWarn([string]$Message) {
    Write-StatusLine -Label "WARN" -Message $Message -Color Yellow
}

function Write-StatusMiss([string]$Message) {
    Write-StatusLine -Label "MISS" -Message $Message -Color Red
}

function Write-Dry([string]$Message) {
    Write-StatusLine -Label "DRY" -Message $Message -Color Cyan
}

function Write-Warn([string]$Message) {
    Write-Warning $Message
}

function Invoke-StepCommand {
    param([Parameter(Mandatory)][string]$Command)
    if ($DryRun) {
        Write-Dry $Command
        return
    }
    pwsh -NoProfile -ExecutionPolicy Bypass -Command $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Command"
    }
}

function Install-WingetPackage {
    param([Parameter(Mandatory)][string]$Id)
    $installCommand = "winget install --id $Id --exact --accept-package-agreements --accept-source-agreements"
    if ($DryRun) {
        Write-Dry $installCommand
        return
    }
    $installed = & winget list --id $Id --exact --accept-source-agreements 2>$null
    if ($LASTEXITCODE -eq 0 -and ($installed -match [regex]::Escape($Id))) {
        Write-StatusOk "$Id already installed"
        return
    }
    & winget install --id $Id --exact --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -eq 0) {
        return
    }
    $installed = & winget list --id $Id --exact --accept-source-agreements 2>$null
    if ($installed -match [regex]::Escape($Id)) {
        Write-StatusOk "$Id already installed"
        return
    }
    throw "winget install failed with exit code ${LASTEXITCODE}: $Id"
}

function Enable-CurrentUserPowerShellScripts {
    $policy = Get-ExecutionPolicy -Scope CurrentUser
    if ($policy -in @("RemoteSigned", "Unrestricted", "Bypass")) {
        Write-StatusOk "PowerShell CurrentUser execution policy allows npm shims ($policy)"
        return
    }
    if ($DryRun) {
        Write-Dry "Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force"
        return
    }
    Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force -ErrorAction SilentlyContinue
    $policy = Get-ExecutionPolicy -Scope CurrentUser
    if ($policy -in @("RemoteSigned", "Unrestricted", "Bypass")) {
        Write-StatusOk "PowerShell CurrentUser execution policy set to $policy for npm command shims"
        $effectivePolicy = Get-ExecutionPolicy
        if ($effectivePolicy -ne $policy) {
            Write-StatusWarn "Current process execution policy is $effectivePolicy; open a new normal PowerShell terminal before launching codex."
        }
        return
    }
    Write-StatusWarn "Could not set CurrentUser execution policy. Launch Codex with codex.cmd, or ask IT/admin to allow RemoteSigned for CurrentUser."
}

function Test-CodexLaunchable {
    Refresh-ProcessPath
    $codex = Get-Command codex -ErrorAction SilentlyContinue
    $codexCmd = Get-Command codex.cmd -ErrorAction SilentlyContinue
    if ($codex) {
        Write-StatusOk "codex command available at $($codex.Source)"
    }
    elseif ($codexCmd) {
        Write-StatusWarn "codex PowerShell shim not launchable; use codex.cmd or rerun step 2"
    }
    else {
        Write-StatusWarn "codex command not found; run step 2"
    }
}

function Refresh-ProcessPath {
    $pathParts = @(
        "$HOME\.dotnet",
        [Environment]::GetEnvironmentVariable("Path", "Machine"),
        [Environment]::GetEnvironmentVariable("Path", "User"),
        [Environment]::GetEnvironmentVariable("Path", "Process"),
        "C:\Program Files\Git\cmd",
        "C:\Program Files\Git\bin",
        "$env:LOCALAPPDATA\Microsoft\WindowsApps"
    ) | Where-Object { $_ }
    $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $merged = foreach ($chunk in $pathParts) {
        foreach ($part in $chunk.Split([System.IO.Path]::PathSeparator)) {
            $trimmed = $part.Trim()
            if ($trimmed -and $seen.Add($trimmed)) {
                $trimmed
            }
        }
    }
    $env:PATH = ($merged -join [System.IO.Path]::PathSeparator)
}

function Get-GitCommandExpression {
    Refresh-ProcessPath
    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($git) {
        return "git"
    }
    foreach ($candidate in @(
        "C:\Program Files\Git\cmd\git.exe",
        "C:\Program Files\Git\bin\git.exe",
        "${env:ProgramFiles}\Git\cmd\git.exe",
        "${env:ProgramFiles}\Git\bin\git.exe"
    )) {
        if ($candidate -and (Test-Path $candidate)) {
            return "& '$candidate'"
        }
    }
    throw "Git is not available. Run step 2 first, then open a new terminal or rerun this script so Git is on PATH."
}

function ConvertTo-GitSafeDirectoryValues {
    param([Parameter(Mandatory)][string]$Directory)
    $values = [System.Collections.Generic.List[string]]::new()
    $resolved = try { (Resolve-Path $Directory -ErrorAction Stop).Path } catch { $Directory }
    foreach ($candidate in @($resolved, $Directory)) {
        if (-not $candidate) {
            continue
        }
        if (-not $values.Contains($candidate)) {
            $values.Add($candidate)
        }
        $slashPath = $candidate.Replace("\", "/")
        if (-not $values.Contains($slashPath)) {
            $values.Add($slashPath)
        }
        if ($slashPath.StartsWith("//") -and -not $values.Contains("%(prefix)$slashPath")) {
            $values.Add("%(prefix)$slashPath")
        }
    }
    return @($values)
}

function Add-GitSafeDirectory {
    param(
        [Parameter(Mandatory)][string]$GitCommand,
        [Parameter(Mandatory)][string]$Directory
    )
    foreach ($safeDirectory in ConvertTo-GitSafeDirectoryValues $Directory) {
        $quoted = $safeDirectory.Replace("'", "''")
        Invoke-StepCommand "$GitCommand config --global --add safe.directory '$quoted'"
    }
}

function Test-GitRepository {
    param([Parameter(Mandatory)][string]$Directory)
    return (Test-Path (Join-Path $Directory ".git"))
}

function Move-NonGitDirectoryAside {
    param([Parameter(Mandatory)][string]$Directory)
    $stamp = Get-Date -Format yyyyMMddHHmmss
    $backup = "$Directory.non-git-$stamp"
    if ($DryRun) {
        Write-Dry "move non-git directory `"$Directory`" to `"$backup`""
        return
    }
    try {
        Move-Item -Path $Directory -Destination $backup -ErrorAction Stop
        Write-StatusWarn "Existing non-git directory moved aside: $backup"
    }
    catch {
        $children = @(Get-ChildItem -LiteralPath $Directory -Force -ErrorAction SilentlyContinue)
        if ($children.Count -eq 0) {
            Remove-Item -LiteralPath $Directory -Force -ErrorAction Stop
            Write-StatusWarn "Removed empty non-git directory: $Directory"
            return
        }
        throw "Could not move existing non-git directory '$Directory'. Original error: $($_.Exception.Message)"
    }
}

function New-CheckoutRootFallback {
    param([Parameter(Mandatory)][string]$CurrentRoot)
    $stamp = Get-Date -Format yyyyMMddHHmmss
    $parent = Split-Path -Parent $CurrentRoot
    $leaf = Split-Path -Leaf $CurrentRoot
    $fallback = Join-Path $parent "$leaf-$stamp"
    Write-StatusWarn "Existing checkout root contains a locked non-git folder. Using fresh checkout root: $fallback"
    if (-not $DryRun) {
        New-Item -ItemType Directory -Force -Path $fallback | Out-Null
    }
    return $fallback
}

function Get-CheckoutRootCandidates {
    $candidates = [System.Collections.Generic.List[string]]::new()
    foreach ($candidate in @($GitHubRoot, (Join-Path $HOME "LocalDocuments\GitHub"))) {
        if ($candidate -and -not $candidates.Contains($candidate)) {
            $candidates.Add($candidate)
        }
    }
    $localDocuments = Join-Path $HOME "LocalDocuments"
    if (Test-Path $localDocuments) {
        Get-ChildItem -LiteralPath $localDocuments -Directory -Filter "GitHub*" -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending |
            ForEach-Object {
                if (-not $candidates.Contains($_.FullName)) {
                    $candidates.Add($_.FullName)
                }
            }
    }
    return @($candidates)
}

function Resolve-CheckoutRepoPath {
    param(
        [Parameter(Mandatory)][string]$RepoName,
        [string]$RequiredChild = ".git"
    )
    foreach ($root in Get-CheckoutRootCandidates) {
        $repoPath = Join-Path $root $RepoName
        $requiredPath = Join-Path $repoPath $RequiredChild
        if (Test-Path $requiredPath) {
            return $repoPath
        }
    }
    return Join-Path $GitHubRoot $RepoName
}

function Resolve-DjconnectRepoRoot {
    return Resolve-CheckoutRepoPath -RepoName "djconnect" -RequiredChild "custom_components\djconnect"
}

function Get-DotNetSdkVersionFromGlobalJson {
    param([Parameter(Mandatory)][string]$Directory)
    $globalJson = Join-Path $Directory "global.json"
    if (-not (Test-Path $globalJson)) {
        return ""
    }
    try {
        $data = Get-Content -Raw -Path $globalJson | ConvertFrom-Json
        return [string]$data.sdk.version
    }
    catch {
        Write-StatusWarn "Could not parse $globalJson ($($_.Exception.Message))"
        return ""
    }
}

function Test-DotNetSdkInstalled {
    param([Parameter(Mandatory)][string]$Version)
    Refresh-ProcessPath
    if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
        return $false
    }
    $sdks = @(& dotnet --list-sdks 2>$null | ForEach-Object { ($_ -split "\s+")[0] })
    return $sdks -contains $Version
}

function Install-DotNetSdkVersion {
    param([Parameter(Mandatory)][string]$Version)
    if (Test-DotNetSdkInstalled $Version) {
        Write-StatusOk ".NET SDK $Version installed"
        return
    }
    $installDir = Join-Path $HOME ".dotnet"
    $installScript = Join-Path $env:TEMP "dotnet-install.ps1"
    Invoke-StepCommand "Invoke-WebRequest -UseBasicParsing https://dot.net/v1/dotnet-install.ps1 -OutFile `"$installScript`""
    Invoke-StepCommand "& `"$installScript`" -Version $Version -InstallDir `"$installDir`""
    if ($DryRun) {
        Write-StatusOk ".NET SDK $Version would be installed to $installDir"
        return
    }
    Refresh-ProcessPath
    if (-not (Test-DotNetSdkInstalled $Version)) {
        throw ".NET SDK $Version was requested by global.json but is still not visible after installation."
    }
    Write-StatusOk ".NET SDK $Version installed"
}

function Ensure-DotNetSdkForDirectory {
    param([Parameter(Mandatory)][string]$Directory)
    $version = Get-DotNetSdkVersionFromGlobalJson $Directory
    if (-not $version) {
        Write-StatusWarn "No global.json SDK version found in $Directory"
        return
    }
    Install-DotNetSdkVersion $version
}

function Invoke-InDirectory {
    param(
        [Parameter(Mandatory)][string]$Directory,
        [Parameter(Mandatory)][string]$Command
    )
    if (-not (Test-Path $Directory)) {
        Write-Warn "Skipping missing directory: $Directory"
        return
    }
    if ($DryRun) {
        Write-Dry "cd `"$Directory`"; $Command"
        return
    }
    Push-Location $Directory
    try {
        pwsh -NoProfile -ExecutionPolicy Bypass -Command $Command
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed with exit code ${LASTEXITCODE}: $Command"
        }
    }
    finally {
        Pop-Location
    }
}

function Invoke-PythonInDirectory {
    param(
        [Parameter(Mandatory)][string]$Directory,
        [Parameter(Mandatory)][string]$Arguments
    )
    $python = Get-PythonCommandExpression
    Invoke-InDirectory $Directory "`$env:PYTHONUTF8='1'; `$env:PYTHONIOENCODING='utf-8'; $python -X utf8 $Arguments"
}

function Get-PythonCommandExpression {
    Refresh-ProcessPath
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        return "py -3.11"
    }
    foreach ($candidate in @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311-arm64\python.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"),
        "C:\Program Files\Python311\python.exe"
    )) {
        if ($candidate -and (Test-Path $candidate)) {
            return "& '$candidate'"
        }
    }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python -and ($python.Source -notlike "*\WindowsApps\python.exe")) {
        return "python"
    }
    throw "Python 3.11 is not available yet. Run step 2 again, open a new terminal, or disable the Microsoft Store python.exe alias under Settings > Apps > Advanced app settings > App execution aliases."
}

function Load-OnboardingEnv {
    if (-not (Test-Path $EnvFile)) {
        return
    }
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            return
        }
        $name, $value = $line.Split("=", 2)
        if (-not [Environment]::GetEnvironmentVariable($name, "Process")) {
            [Environment]::SetEnvironmentVariable($name, $value.Trim('"'), "Process")
        }
    }
}

function Save-Secret {
    param([Parameter(Mandatory)][string]$Name, [Parameter(Mandatory)][string]$Value)
    if ($DryRun) {
        Write-Dry "save $Name to $EnvFile"
        return
    }
    $dir = Split-Path -Parent $EnvFile
    if ($dir) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    if (-not (Test-Path $EnvFile)) {
        New-Item -ItemType File -Path $EnvFile | Out-Null
    }
    $existing = Get-Content $EnvFile -ErrorAction SilentlyContinue
    $filtered = @($existing | Where-Object { $_ -notmatch "^$([regex]::Escape($Name))=" })
    $filtered + "$Name=`"$Value`"" | Set-Content -Path $EnvFile -Encoding UTF8
}

function Prompt-SecretsIfRequested {
    if (-not $PromptSecrets) {
        return
    }
    Load-OnboardingEnv
    foreach ($name in @("NGROK_AUTHTOKEN", "DJCONNECT_HA_TOKEN")) {
        if ([Environment]::GetEnvironmentVariable($name, "Process")) {
            continue
        }
        $value = Read-Host "$name (leave empty to skip)"
        if ($value) {
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
            Save-Secret -Name $name -Value $value
        }
    }
}

function Confirm-Step([string]$Prompt) {
    if ($Yes) {
        return $true
    }
    $reply = Read-Host "$Prompt [Y/n]"
    return -not $reply -or $reply -match "^(y|yes)$"
}

function Test-WritableDirectory {
    param(
        [Parameter(Mandatory)][string]$Label,
        [Parameter(Mandatory)][string]$Directory
    )
    try {
        New-Item -ItemType Directory -Force -Path $Directory | Out-Null
        $probe = Join-Path $Directory ".djconnect-preflight-write-test"
        Set-Content -Path $probe -Value "ok" -Encoding ASCII
        Remove-Item -Force $probe
        Write-StatusOk "$Label writable via $Directory"
    }
    catch {
        Write-StatusMiss "$Label not writable via $Directory ($($_.Exception.Message))"
    }
}

function Test-DiskFree {
    param(
        [Parameter(Mandatory)][string]$Path,
        [int]$MinimumGb = 20
    )
    try {
        $resolved = Resolve-Path -Path $Path -ErrorAction SilentlyContinue
        $target = if ($resolved) { $resolved.Path } else { $Path }
        $root = [System.IO.Path]::GetPathRoot($target)
        $driveName = $root.TrimEnd([char[]]@(":", "\"))
        $drive = Get-PSDrive -Name $driveName -ErrorAction Stop
        $freeGb = [math]::Round($drive.Free / 1GB)
        if ($freeGb -lt $MinimumGb) {
            Write-StatusWarn "disk free ${freeGb}GB at $root; ${MinimumGb}GB+ recommended"
        }
        else {
            Write-StatusOk "disk free ${freeGb}GB at $root"
        }
    }
    catch {
        Write-StatusMiss "disk free check failed for $Path ($($_.Exception.Message))"
    }
}

function Test-PortStatus {
    param(
        [Parameter(Mandatory)][int]$Port,
        [Parameter(Mandatory)][string]$Purpose
    )
    try {
        $used = @(Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue)
        if ($used.Count -gt 0) {
            $processNames = @($used | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
                try { (Get-Process -Id $_ -ErrorAction Stop).ProcessName } catch { "pid $_" }
            })
            Write-StatusOk "port $Port already used by $($processNames -join ', ')"
        }
        else {
            Write-StatusOk "port $Port free for $Purpose"
        }
    }
    catch {
        Write-StatusWarn "port $Port check failed for $Purpose ($($_.Exception.Message))"
    }
}

function Test-NetworkEndpoint {
    param(
        [Parameter(Mandatory)][string]$Label,
        [Parameter(Mandatory)][string]$Url,
        [int[]]$ExpectedStatus = @(200)
    )
    try {
        $response = Invoke-WebRequest -Uri $Url -Method Head -UseBasicParsing -TimeoutSec 10 -MaximumRedirection 3 -ErrorAction Stop
        if ($ExpectedStatus -contains [int]$response.StatusCode) {
            Write-StatusOk "network $Label`t$Url ($($response.StatusCode))"
        }
        else {
            Write-StatusWarn "network $Label`t$Url returned $($response.StatusCode)"
        }
    }
    catch {
        $statusCode = $null
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $statusCode = [int]$_.Exception.Response.StatusCode
        }
        if ($statusCode -and ($ExpectedStatus -contains $statusCode)) {
            Write-StatusOk "network $Label`t$Url ($statusCode)"
        }
        elseif ($statusCode) {
            Write-StatusWarn "network $Label`t$Url returned $statusCode"
        }
        else {
            Write-StatusMiss "network $Label`t$Url failed ($($_.Exception.Message))"
        }
    }
}

function Test-HttpService {
    param(
        [Parameter(Mandatory)][string]$Label,
        [Parameter(Mandatory)][string]$Url,
        [int[]]$ExpectedStatus = @(200, 302, 401)
    )
    if ($DryRun) {
        Write-Dry "curl.exe -fsS $Url"
        return
    }
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10 -MaximumRedirection 3 -ErrorAction Stop
        if ($ExpectedStatus -contains [int]$response.StatusCode) {
            Write-StatusOk "$Label reachable at $Url ($($response.StatusCode))"
        }
        else {
            Write-StatusWarn "$Label reachable at $Url but returned $($response.StatusCode)"
        }
    }
    catch {
        $statusCode = $null
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $statusCode = [int]$_.Exception.Response.StatusCode
        }
        if ($statusCode -and ($ExpectedStatus -contains $statusCode)) {
            Write-StatusOk "$Label reachable at $Url ($statusCode)"
        }
        elseif ($statusCode) {
            Write-StatusWarn "$Label at $Url returned $statusCode"
        }
        else {
            Write-StatusMiss "$Label not reachable at $Url ($($_.Exception.Message))"
        }
    }
}

function Ensure-ComposeFile {
    if ($DryRun) {
        Write-Dry "add missing homeassistant, whisper, piper and music-assistant services to $HaComposeFile"
        return
    }
    $dir = Split-Path -Parent $HaComposeFile
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    if (-not (Test-Path $HaComposeFile)) {
        @"
services:
  homeassistant:
    image: ghcr.io/home-assistant/home-assistant:stable
    container_name: homeassistant
    network_mode: host
    volumes:
      - ${HaConfigDir}:/config
    restart: unless-stopped
  whisper:
    image: rhasspy/wyoming-whisper
    container_name: wyoming-whisper
    command: --model tiny-int8 --language nl
    ports:
      - "10300:10300"
    restart: unless-stopped
  piper:
    image: rhasspy/wyoming-piper
    container_name: wyoming-piper
    command: --voice nl_NL-mls-medium
    ports:
      - "10200:10200"
    restart: unless-stopped
  music-assistant:
    image: ghcr.io/music-assistant/server:latest
    container_name: music-assistant-server
    volumes:
      - ${MaDataDir}:/data
    ports:
      - "8095:8095"
    restart: unless-stopped
"@ | Set-Content -Path $HaComposeFile -Encoding UTF8
    }
}

function Configure-HaNgrokNetwork {
    param([Parameter(Mandatory)][string]$ExternalUrl)
    $configPath = Join-Path $HaConfigDir "configuration.yaml"
    if ($DryRun) {
        Write-Dry "configure Home Assistant external/internal URL and trusted proxy settings as $ExternalUrl"
        return
    }
    New-Item -ItemType Directory -Force -Path $HaConfigDir | Out-Null
    if (-not (Test-Path $configPath)) {
        New-Item -ItemType File -Path $configPath | Out-Null
    }
    $block = @"

homeassistant:
  external_url: "$ExternalUrl"
  internal_url: "$ExternalUrl"

http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 127.0.0.1
    - ::1
"@
    Add-Content -Path $configPath -Value $block
}

function Step-0-Preflight {
    Write-Info "Running Windows machine, hardware, filesystem and network preflight."
    if (-not $IsWindows) {
        Write-Warn "This script is intended for Windows 11; continuing because PowerShell is cross-platform."
    }

    if ($IsWindows) {
        try {
            $os = Get-CimInstance Win32_OperatingSystem
            $computer = Get-CimInstance Win32_ComputerSystem
            $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
            Write-Info "Host: $($os.Caption) $($os.Version), arch $env:PROCESSOR_ARCHITECTURE"
            if ($os.Caption -match "Windows 11") {
                Write-StatusOk "$($os.Caption) $($os.Version)"
            }
            else {
                Write-StatusWarn "$($os.Caption) $($os.Version); Windows 11 is recommended"
            }
            $ramGb = [math]::Round($computer.TotalPhysicalMemory / 1GB)
            if ($ramGb -lt 8) {
                Write-StatusMiss "RAM ${ramGb}GB; minimum is 8GB"
            }
            elseif ($ramGb -lt 16) {
                Write-StatusWarn "RAM ${ramGb}GB; 16GB+ recommended for Docker + .NET MAUI"
            }
            else {
                Write-StatusOk "RAM ${ramGb}GB"
            }
            Write-StatusOk "CPU cores $($cpu.NumberOfLogicalProcessors)"
            if ($computer.Model -match "Virtual|Parallels|VMware|VirtualBox|Hyper-V") {
                Write-StatusOk "VM detected: $($computer.Manufacturer) $($computer.Model)"
            }
        }
        catch {
            Write-StatusWarn "Windows hardware/OS inspection failed ($($_.Exception.Message))"
        }
    }

    foreach ($cmd in @("git", "pwsh", "node", "npm", "codex")) {
        Refresh-ProcessPath
        if (Get-Command $cmd -ErrorAction SilentlyContinue) {
            Write-StatusOk "$cmd available"
        }
        else {
            Write-StatusWarn "$cmd missing"
        }
    }

    Test-WritableDirectory -Label "GitHub root" -Directory $GitHubRoot
    if ($LogFile) {
        Test-WritableDirectory -Label "Log dir" -Directory (Split-Path -Parent $LogFile)
    }
    Test-WritableDirectory -Label "Home Assistant config parent" -Directory (Split-Path -Parent $HaConfigDir)
    Test-WritableDirectory -Label "Env file parent" -Directory (Split-Path -Parent $EnvFile)
    Test-DiskFree -Path $GitHubRoot

    Test-PortStatus -Port 8123 -Purpose "Home Assistant"
    Test-PortStatus -Port 8095 -Purpose "music-assistant-server"
    Test-PortStatus -Port 8787 -Purpose "Cloudflare Worker dev"
    Test-PortStatus -Port 8080 -Purpose "static website preview"
    Test-PortStatus -Port 18080 -Purpose "DJConnect Pi local API"

    Test-NetworkEndpoint -Label "GitHub" -Url "https://github.com"
    Test-NetworkEndpoint -Label "GitHub raw" -Url "https://raw.githubusercontent.com"
    Test-NetworkEndpoint -Label "winget CDN" -Url "https://cdn.winget.microsoft.com" -ExpectedStatus @(200, 404)
    Test-NetworkEndpoint -Label "npm" -Url "https://registry.npmjs.org"
    Test-NetworkEndpoint -Label "PyPI" -Url "https://pypi.org"
    Test-NetworkEndpoint -Label "GHCR" -Url "https://ghcr.io/v2/" -ExpectedStatus @(200, 401, 405)
    Test-NetworkEndpoint -Label "Docker Hub" -Url "https://registry-1.docker.io/v2/" -ExpectedStatus @(200, 401)
    Test-NetworkEndpoint -Label "Cloudflare" -Url "https://api.cloudflare.com/client/v4/user/tokens/verify" -ExpectedStatus @(200, 400, 401)
    Test-NetworkEndpoint -Label "Microsoft Store" -Url "https://storeedgefd.dsx.mp.microsoft.com" -ExpectedStatus @(200, 404)
    Test-CodexLaunchable
}

function Step-1-PackageManager {
    Write-Info "Installing/checking Windows package manager tooling."
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Warn "winget is missing. Install App Installer from Microsoft Store first."
        return
    }
    Invoke-StepCommand "winget source update"
}

function Step-2-Tooling {
    Write-Info "Installing developer tooling with winget."
    foreach ($id in @(
        "Git.Git",
        "GitHub.cli",
        "Python.Python.3.11",
        "OpenJS.NodeJS.LTS",
        "Microsoft.DotNet.SDK.10",
        "Microsoft.PowerShell"
    )) {
        Install-WingetPackage $id
    }
    Refresh-ProcessPath
    if (Get-Command git -ErrorAction SilentlyContinue) {
        Write-StatusOk "git available after PATH refresh"
    }
    elseif (Test-Path "C:\Program Files\Git\cmd\git.exe") {
        Write-StatusOk "git installed at C:\Program Files\Git\cmd\git.exe"
    }
    else {
        Write-StatusWarn "git still not visible after install; open a new terminal and rerun step 0/3"
    }
    Refresh-ProcessPath
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Invoke-StepCommand "npm install -g @openai/codex"
        Enable-CurrentUserPowerShellScripts
        Refresh-ProcessPath
        if (Get-Command codex -ErrorAction SilentlyContinue) {
            Write-StatusOk "codex available after npm install"
        }
        else {
            $codexCmd = Get-Command codex.cmd -ErrorAction SilentlyContinue
            if ($codexCmd) {
                Write-StatusWarn "Codex installed but PowerShell may prefer a blocked codex.ps1 shim. Open a new terminal or run codex.cmd."
            }
            else {
                Write-StatusWarn "Codex installed, but 'codex' is not on PATH yet. Open a new terminal or check npm global bin."
            }
        }
    }
    else {
        Write-StatusWarn "npm is not available yet; open a new terminal and rerun step 2 to install Codex CLI."
    }
}

function Step-3-Repos {
    Write-Info "Cloning/updating DJConnect repositories."
    $checkoutRoot = $GitHubRoot
    if ($checkoutRoot -like "C:\Mac\Home\*") {
        throw "GitHubRoot points to the Parallels shared Mac folder ($checkoutRoot). Use a local Windows path, for example $HOME\LocalDocuments\GitHub."
    }
    $homeRoot = $HOME.TrimEnd("\")
    if (-not ($checkoutRoot -like "$homeRoot\*")) {
        throw "GitHubRoot must be under the current user's home directory. Current value: $checkoutRoot. Use $HOME\LocalDocuments\GitHub."
    }
    $gitCmd = Get-GitCommandExpression
    $repos = @(
        "djconnect",
        "djconnect-app",
        "djconnect-windows",
        "djconnect-pi",
        "djconnect-esp32",
        "djconnect-website",
        "djconnect-api"
    )
    while ($true) {
        Write-StatusOk "Windows-local checkout root: $checkoutRoot"
        New-Item -ItemType Directory -Force -Path $checkoutRoot | Out-Null
        $needsFreshRoot = $false
        foreach ($repo in $repos) {
            $dir = Join-Path $checkoutRoot $repo
            if ((Test-Path $dir) -and -not (Test-GitRepository $dir)) {
                try {
                    Move-NonGitDirectoryAside $dir
                }
                catch {
                    $checkoutRoot = New-CheckoutRootFallback $checkoutRoot
                    $needsFreshRoot = $true
                    break
                }
            }
        }
        if (-not $needsFreshRoot) {
            break
        }
    }
    $script:GitHubRoot = $checkoutRoot
    $script:RepoRoot = Join-Path $checkoutRoot "djconnect"
    foreach ($repo in $repos) {
        $dir = Join-Path $checkoutRoot $repo
        if (Test-Path $dir) {
            if (Test-GitRepository $dir) {
                Add-GitSafeDirectory -GitCommand $gitCmd -Directory $dir
                Invoke-InDirectory $dir "$gitCmd fetch --all --prune"
            }
            else {
                Move-NonGitDirectoryAside $dir
                Invoke-InDirectory $checkoutRoot "$gitCmd clone https://github.com/pcvantol/$repo.git"
                Add-GitSafeDirectory -GitCommand $gitCmd -Directory $dir
            }
        }
        else {
            Invoke-InDirectory $checkoutRoot "$gitCmd clone https://github.com/pcvantol/$repo.git"
            Add-GitSafeDirectory -GitCommand $gitCmd -Directory $dir
        }
    }
}

function Step-4-Python {
    Write-Info "Preparing Python test environment."
    $repoRoot = Resolve-DjconnectRepoRoot
    Invoke-PythonInDirectory $repoRoot "-m pip install --upgrade pip"
}

function Step-5-Tests {
    Write-Info "Running Home Assistant integration tests."
    $repoRoot = Resolve-DjconnectRepoRoot
    Invoke-PythonInDirectory $repoRoot "-m unittest discover -s tests"
}

function Step-6-Maui {
    Write-Info "Installing .NET MAUI workloads."
    $dir = Resolve-CheckoutRepoPath -RepoName "djconnect-windows" -RequiredChild "DJConnect.Windows.sln"
    $solution = Join-Path $dir "DJConnect.Windows.sln"
    if (Test-Path $solution) {
        Ensure-DotNetSdkForDirectory $dir
        Invoke-StepCommand "dotnet workload install maui"
        Invoke-InDirectory $dir "dotnet workload restore `"DJConnect.Windows.sln`""
    }
    else {
        Write-StatusWarn "Windows client solution not found at $solution; run step 3 first, then rerun step 6 for workload restore."
        Invoke-StepCommand "dotnet workload install maui"
    }
}

function Step-7-WindowsClient {
    Write-Info "Running Windows client validation."
    $dir = Resolve-CheckoutRepoPath -RepoName "djconnect-windows" -RequiredChild "DJConnect.Windows.sln"
    Invoke-InDirectory $dir "dotnet restore DJConnect.Windows.sln"
    Invoke-InDirectory $dir "dotnet format DJConnect.Windows.sln --verify-no-changes --no-restore"
    Invoke-InDirectory $dir "dotnet test DJConnect.Windows.sln --no-restore"
}

function Step-8-HomeAssistant {
    Write-Info "Checking Home Assistant published by the macOS host."
    Write-Host "Windows ARM in Parallels cannot run Docker Desktop nested virtualization reliably."
    Write-Host "Start the Docker stack on macOS, then reach it from Windows through the Parallels host URL."
    Write-Host "Home Assistant host URL: $HaHostUrl"
    Test-HttpService -Label "Home Assistant" -Url $HaHostUrl -ExpectedStatus @(200, 302, 401)
}

function Step-9-SyncIntegration {
    Write-Info "Syncing DJConnect integration into local Home Assistant config."
    $repoRoot = Resolve-DjconnectRepoRoot
    $target = Join-Path $HaConfigDir "custom_components\djconnect"
    if ($DryRun) {
        Write-Dry "sync $repoRoot\custom_components\djconnect to $target"
        return
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    if (Test-Path $target) {
        Remove-Item -Recurse -Force $target
    }
    Copy-Item -Recurse -Force (Join-Path $repoRoot "custom_components\djconnect") $target
}

function Step-10-Hacs {
    Write-Info "Installing HACS in local Home Assistant config."
    $customComponents = Join-Path $HaConfigDir "custom_components"
    Invoke-StepCommand "New-Item -ItemType Directory -Force -Path `"$customComponents`""
    Invoke-StepCommand "Invoke-WebRequest -UseBasicParsing https://get.hacs.xyz -OutFile `"$env:TEMP\hacs.ps1`""
    Write-Warn "HACS upstream installer is shell-oriented; if this step fails, follow https://hacs.xyz/docs/use/download/download/ manually."
}

function Step-11-VoiceBackend {
    Write-Info "Checking voice/backend services published by the macOS host."
    Write-Host "Home Assistant host URL: $HaHostUrl"
    Write-Host "Music Assistant host URL: $MaHostUrl"
    Test-HttpService -Label "Home Assistant" -Url $HaHostUrl -ExpectedStatus @(200, 302, 401)
    Test-HttpService -Label "Music Assistant" -Url $MaHostUrl -ExpectedStatus @(200, 302, 401)
}

function Step-12-Ngrok {
    Write-Info "Installing/starting persistent ngrok tunnel for local Home Assistant."
    $token = [Environment]::GetEnvironmentVariable("NGROK_AUTHTOKEN", "Process")
    if (-not $token) {
        throw "NGROK_AUTHTOKEN is required. Run with -PromptSecrets or export it from your ngrok dashboard."
    }
    if (-not (Get-Command ngrok -ErrorAction SilentlyContinue)) {
        Install-WingetPackage "Ngrok.Ngrok"
    }
    if ($DryRun) {
        Write-Dry "ngrok config add-authtoken <redacted>"
    }
    else {
        & ngrok config add-authtoken $token
    }
    $ngrokArgs = if ($NgrokDomain) { "http --url=$NgrokDomain 8123" } else { "http 8123" }
    Invoke-StepCommand "schtasks /Create /TN `"DJConnect Home Assistant ngrok`" /SC ONLOGON /TR `"ngrok $ngrokArgs`" /F"
    if ($NgrokDomain) {
        Configure-HaNgrokNetwork "https://$NgrokDomain"
    }
    else {
        Write-Host "Open http://127.0.0.1:4040 and copy the HTTPS Forwarding URL into Home Assistant."
    }
}

function Step-13-E2E {
    Write-Info "Running local E2E release/build smoke checks."
    $repoRoot = Resolve-DjconnectRepoRoot
    Invoke-PythonInDirectory $repoRoot "-m unittest tests.test_ask_dj_e2e_contract"
    Invoke-InDirectory $repoRoot ".\release.sh $E2EVersion --dry-run"
    if ($env:DJCONNECT_HA_WS_URL -and $env:DJCONNECT_HA_TOKEN) {
        Write-Host "DJCONNECT_HA_WS_URL=$($env:DJCONNECT_HA_WS_URL)"
        Write-Host "DJCONNECT_HA_TOKEN=<redacted>"
    }
}

function Step-14-CiSmoke {
    if (-not $RunCiPush) {
        throw "Step 14 requires -RunCiPush."
    }
    Write-Info "Pushing CI smoke branch."
    $gitCmd = Get-GitCommandExpression
    $repoRoot = Resolve-DjconnectRepoRoot
    Invoke-InDirectory $repoRoot "$gitCmd switch -c $CiBranch"
    Invoke-InDirectory $repoRoot "$gitCmd commit --allow-empty -m `"CI smoke test for Windows onboarding script`""
    Invoke-InDirectory $repoRoot "$gitCmd push -u origin $CiBranch"
}

function Get-SelectedSteps {
    if ($Steps) {
        return @($Steps.Split(",") | ForEach-Object { [int]$_.Trim() })
    }
    if ($All) {
        return @($Script:StepCatalog.Keys)
    }
    if ($Core) {
        return @(0, 1, 2, 3, 4, 5, 8, 9, 10, 11)
    }
    return @(0)
}

function Invoke-StepByNumber([int]$Step) {
    switch ($Step) {
        0 { Step-0-Preflight }
        1 { Step-1-PackageManager }
        2 { Step-2-Tooling }
        3 { Step-3-Repos }
        4 { Step-4-Python }
        5 { Step-5-Tests }
        6 { Step-6-Maui }
        7 { Step-7-WindowsClient }
        8 { Step-8-HomeAssistant }
        9 { Step-9-SyncIntegration }
        10 { Step-10-Hacs }
        11 { Step-11-VoiceBackend }
        12 { Step-12-Ngrok }
        13 { Step-13-E2E }
        14 { Step-14-CiSmoke }
        default { throw "Unknown step: $Step" }
    }
}

if ($Library) {
    return
}

if ($Help) {
    Write-Usage
    exit 0
}

Load-OnboardingEnv
Prompt-SecretsIfRequested

if ($LogFile -and -not $Plan) {
    $logDir = Split-Path -Parent $LogFile
    if ($logDir) {
        New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    }
    Start-Transcript -Path $LogFile -Append | Out-Null
}

try {
    if (-not $All -and -not $Core -and -not $Steps -and -not $Plan) {
        Invoke-InteractiveMenu
        exit 0
    }

    $selected = Get-SelectedSteps
    if ($Plan) {
        foreach ($step in $selected) {
            if (-not $Script:StepCatalog.Contains($step)) {
                throw "Unknown step: $step"
            }
            "{0} {1,2}. {2}" -f "PLAN", $step, $Script:StepCatalog[$step]
        }
        exit 0
    }

    Invoke-Steps -SelectedSteps $selected
}
finally {
    if ($LogFile -and -not $Plan) {
        Stop-Transcript | Out-Null
    }
}

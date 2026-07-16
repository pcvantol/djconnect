#!/usr/bin/env pwsh
#Requires -Version 7.0

[CmdletBinding()]
param(
    [string] $GitHubRoot = 'C:\DJConnect\source',
    [string] $RunnerRoot = 'C:\actions-runner-arm64',
    [string] $InstallRoot = 'C:\DJConnect\internal-release',
    [switch] $DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$organization = 'pcvantol'
$repository = 'djconnect-windows'
$runnerName = 'djconnect-windows11-parallels-arm64'
$runnerLabels = 'internal-release,qualification,windows11,parallels,arm64'

function Write-Info([string] $Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Invoke-Action {
    param([Parameter(Mandatory)][scriptblock] $Command)
    if ($DryRun) {
        Write-Host "DRY: $($Command.ToString().Trim())" -ForegroundColor Yellow
        return
    }
    & $Command
}

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not $IsWindows) {
    throw 'This bootstrap runs only on Windows.'
}
if (-not (Test-IsAdministrator)) {
    throw 'Run this bootstrap from an elevated PowerShell 7 session.'
}
if ($env:PROCESSOR_ARCHITECTURE -ne 'ARM64') {
    throw "This runner must be native Windows ARM64; observed PROCESSOR_ARCHITECTURE=$($env:PROCESSOR_ARCHITECTURE)."
}

function Ensure-WingetPackage([string] $PackageId, [string] $Description) {
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if ($null -eq $winget) {
        throw 'winget.exe is required to bootstrap the Windows runner.'
    }
    Write-Info "Installing or updating $Description."
    Invoke-Action {
        & $winget.Source install --id $PackageId --exact --source winget --scope machine --silent --disable-interactivity --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) {
            & $winget.Source upgrade --id $PackageId --exact --source winget --scope machine --silent --disable-interactivity --accept-package-agreements --accept-source-agreements
            if ($LASTEXITCODE -ne 0) {
                throw "winget could not install or upgrade $PackageId."
            }
        }
    }
}

Ensure-WingetPackage 'Microsoft.PowerShell' 'PowerShell 7'
Ensure-WingetPackage 'GitHub.cli' 'GitHub CLI'
Ensure-WingetPackage 'Git.Git' 'Git for Windows'

$ghPath = Join-Path $env:ProgramFiles 'GitHub CLI\gh.exe'
if (-not $DryRun -and -not (Test-Path $ghPath)) {
    $gh = Get-Command gh.exe -ErrorAction SilentlyContinue
    if ($null -eq $gh) {
        throw 'GitHub CLI is unavailable after installation.'
    }
    $ghPath = $gh.Source
}

if (-not $DryRun) {
    & $ghPath auth status --hostname github.com *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Info 'Authenticate GitHub CLI in the browser with the DJConnect repository administrator account.'
        & $ghPath auth login --hostname github.com --git-protocol https --web
        if ($LASTEXITCODE -ne 0) {
            throw 'GitHub CLI authentication did not complete.'
        }
    }
}

if (Test-Path (Join-Path $RunnerRoot '.runner')) {
    throw "A runner is already configured in $RunnerRoot. Preserve it or remove it through GitHub before re-running this bootstrap."
}
if ((Test-Path $RunnerRoot) -and -not $DryRun) {
    throw "$RunnerRoot exists but is not a configured runner. Move it aside before re-running this bootstrap."
}

Write-Info 'Creating service-readable runner and internal-release directories.'
Invoke-Action {
    New-Item -ItemType Directory -Force -Path $RunnerRoot, $InstallRoot | Out-Null
    & icacls.exe $RunnerRoot /grant 'NT AUTHORITY\NETWORK SERVICE:(OI)(CI)M' | Out-Null
    & icacls.exe $InstallRoot /grant 'NT AUTHORITY\NETWORK SERVICE:(OI)(CI)M' | Out-Null
}

if ($DryRun) {
    Write-Host 'DRY: fetch the latest actions/runner win-arm64 release and registration token through authenticated GitHub CLI.' -ForegroundColor Yellow
    Write-Host "DRY: configure $runnerName as a NETWORK SERVICE Windows service with labels $runnerLabels." -ForegroundColor Yellow
    Write-Host 'DRY: clone pcvantol/djconnect-windows and run its Windows tooling-maintenance installer.' -ForegroundColor Yellow
    exit 0
}

$release = & $ghPath api 'repos/actions/runner/releases/latest' | ConvertFrom-Json
$assetName = "actions-runner-win-arm64-$($release.tag_name).zip"
$asset = @($release.assets | Where-Object { $_.name -eq $assetName })[0]
if ($null -eq $asset -or $asset.digest -notmatch '^sha256:[0-9a-fA-F]{64}$') {
    throw "GitHub release metadata does not provide a SHA-256 digest for $assetName."
}
$registrationToken = (& $ghPath api --method POST "repos/$organization/$repository/actions/runners/registration-token" --jq '.token').Trim()
if (-not $registrationToken) {
    throw 'GitHub did not return a runner registration token.'
}

$archivePath = Join-Path $env:TEMP $assetName
try {
    Write-Info "Downloading and verifying $assetName."
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $archivePath
    $actualDigest = "sha256:$((Get-FileHash -Algorithm SHA256 -Path $archivePath).Hash.ToLowerInvariant())"
    if ($actualDigest -ne $asset.digest.ToLowerInvariant()) {
        throw 'Actions runner archive SHA-256 does not match GitHub release metadata.'
    }
    Expand-Archive -Path $archivePath -DestinationPath $RunnerRoot -Force
} finally {
    Remove-Item -Force -ErrorAction SilentlyContinue $archivePath
}

Write-Info 'Registering the Windows ARM64 Actions runner as NETWORK SERVICE.'
Push-Location $RunnerRoot
try {
    & .\config.cmd --unattended --replace --url "https://github.com/$organization/$repository" --token $registrationToken --name $runnerName --labels $runnerLabels --work _work --runasservice --windowslogonaccount 'NT AUTHORITY\NETWORK SERVICE'
    if ($LASTEXITCODE -ne 0) {
        throw "Runner configuration failed with exit code $LASTEXITCODE."
    }
} finally {
    Remove-Variable registrationToken -ErrorAction SilentlyContinue
    Pop-Location
}

Write-Info 'Cloning the Windows consumer repository and installing machine tooling maintenance.'
$windowsRepository = Join-Path $GitHubRoot $repository
if (-not (Test-Path (Join-Path $windowsRepository '.git'))) {
    New-Item -ItemType Directory -Force -Path $GitHubRoot | Out-Null
    & $ghPath repo clone "$organization/$repository" $windowsRepository -- --branch main
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not clone the Windows consumer repository.'
    }
}
& (Join-Path $windowsRepository 'scripts\runner\Install-DJConnectPowerShell7Maintenance.ps1') -RunNow

Write-Info 'Restoring the Windows MAUI workload for the checked-out source.'
$dotnetPath = Join-Path $env:ProgramFiles 'dotnet\dotnet.exe'
if (-not (Test-Path $dotnetPath)) {
    throw 'The machine .NET SDK is unavailable after maintenance.'
}
& $dotnetPath workload restore (Join-Path $windowsRepository 'src\DJConnect.Windows\DJConnect.Windows.csproj') '-p:TargetFramework=net10.0-windows10.0.19041.0'
if ($LASTEXITCODE -ne 0) {
    throw "Windows MAUI workload restore failed with exit code $LASTEXITCODE."
}

$serviceName = (Get-Content (Join-Path $RunnerRoot '.service')).Trim()
$service = Get-Service -Name $serviceName
if ($service.Status -ne 'Running') {
    throw "Runner service $serviceName is not running."
}
Write-Host "Windows runner $runnerName is online as service $serviceName." -ForegroundColor Green

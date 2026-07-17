#!/usr/bin/env pwsh
#Requires -Version 7.0

[CmdletBinding()]
param(
    [string] $GitHubRoot = 'C:\DJConnect\source',
    [string] $RunnerRoot = 'C:\actions-runner-arm64',
    [string] $InstallRoot = 'C:\DJConnect\internal-release',
    [switch] $MigrateExistingService,
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

function Invoke-Sc {
    param([Parameter(Mandatory)][string[]] $Arguments)
    if ($DryRun) {
        Write-Host "DRY: sc.exe $($Arguments -join ' ')" -ForegroundColor Yellow
        return
    }
    & sc.exe @Arguments | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "sc.exe $($Arguments[0]) failed with exit code $LASTEXITCODE."
    }
}

function Set-ServiceVirtualAccountLogon {
    param(
        [Parameter(Mandatory)][string] $ServiceName,
        [Parameter(Mandatory)][string] $ServiceIdentity
    )

    # The Service Control Manager requires the literal native command-line
    # form `password= ""` for a passwordless virtual service account. Passing
    # an empty PowerShell array item either fails parameter binding or omits the
    # required quotes before sc.exe parses its arguments.
    $scExe = Join-Path $env:SystemRoot 'System32\sc.exe'
    $configArguments = "config `"$ServiceName`" obj= `"$ServiceIdentity`" password= `"`""
    if ($DryRun) {
        Write-Host "DRY: $scExe $configArguments" -ForegroundColor Yellow
        return
    }

    $process = Start-Process -FilePath $scExe -ArgumentList $configArguments -NoNewWindow -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        throw "sc.exe config failed with exit code $($process.ExitCode)."
    }
}

function Get-RunnerServiceName {
    $serviceFile = Join-Path $RunnerRoot '.service'
    if (-not (Test-Path $serviceFile)) {
        throw "Runner service metadata is absent at $serviceFile."
    }
    $name = (Get-Content -Raw $serviceFile).Trim()
    if ([string]::IsNullOrWhiteSpace($name)) {
        throw "Runner service metadata at $serviceFile is empty."
    }
    return $name
}

function Set-RunnerServiceVirtualAccount {
    param([Parameter(Mandatory)][string] $ServiceName)

    $serviceIdentity = "NT SERVICE\$ServiceName"
    Write-Info "Hardening $ServiceName with dedicated virtual account $serviceIdentity."

    if ($DryRun) {
        Write-Host "DRY: stop $ServiceName; set its service SID to unrestricted; run it as $serviceIdentity; grant only that identity Modify on $RunnerRoot and $InstallRoot; remove explicit NETWORK SERVICE grants; restart and verify." -ForegroundColor Yellow
        return
    }

    $service = Get-Service -Name $ServiceName -ErrorAction Stop
    if ($service.Status -ne 'Stopped') {
        Stop-Service -Name $ServiceName -Force -ErrorAction Stop
        $service.WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
    }

    # A service SID is a passwordless, per-service identity. It is intentionally
    # not a local administrator or an interactive user account.
    Invoke-Sc -Arguments @('sidtype', $ServiceName, 'unrestricted')
    Set-ServiceVirtualAccountLogon -ServiceName $ServiceName -ServiceIdentity $serviceIdentity

    foreach ($path in @($RunnerRoot, $InstallRoot)) {
        New-Item -ItemType Directory -Force -Path $path | Out-Null
        $grant = '{0}:(OI)(CI)M' -f $serviceIdentity
        & icacls.exe $path /grant $grant | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw "Could not grant $serviceIdentity least-privilege access to $path."
        }
        # The bootstrap used NETWORK SERVICE only to start a newly registered
        # service before its name was known. It must not retain write access.
        & icacls.exe $path /remove:g 'NT AUTHORITY\NETWORK SERVICE' | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw "Could not remove the obsolete NETWORK SERVICE grant from $path."
        }
    }

    Start-Service -Name $ServiceName -ErrorAction Stop
    $service = Get-CimInstance Win32_Service -Filter "Name='$ServiceName'" -ErrorAction Stop
    if ($service.StartName -ne $serviceIdentity) {
        throw "Service account verification failed: expected $serviceIdentity, observed $($service.StartName)."
    }
    if ((Get-Service -Name $ServiceName).Status -ne 'Running') {
        throw "Runner service $ServiceName did not reach Running state after virtual-account migration."
    }
    Write-Host "Runner service $ServiceName now runs as $serviceIdentity with scoped filesystem access." -ForegroundColor Green
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

if ($MigrateExistingService) {
    if (-not (Test-Path (Join-Path $RunnerRoot '.runner'))) {
        throw "No configured runner exists at $RunnerRoot. Omit -MigrateExistingService for first-time registration."
    }
    Set-RunnerServiceVirtualAccount -ServiceName (Get-RunnerServiceName)
    exit 0
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
Ensure-WingetPackage 'Python.Python.3.12' 'Python 3.12'
Ensure-WingetPackage 'OpenJS.NodeJS.LTS' 'Node.js LTS'

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
    # Temporary bootstrap access is removed immediately after the runner's
    # service name is available and its dedicated virtual identity is applied.
    & icacls.exe $RunnerRoot /grant 'NT AUTHORITY\NETWORK SERVICE:(OI)(CI)M' | Out-Null
    & icacls.exe $InstallRoot /grant 'NT AUTHORITY\NETWORK SERVICE:(OI)(CI)M' | Out-Null
}

if ($DryRun) {
    Write-Host 'DRY: fetch the latest actions/runner win-arm64 release and registration token through authenticated GitHub CLI.' -ForegroundColor Yellow
    Write-Host "DRY: temporarily register $runnerName as a service, then migrate it to a dedicated passwordless virtual service account with labels $runnerLabels." -ForegroundColor Yellow
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

Write-Info 'Registering the Windows ARM64 Actions runner service.'
Push-Location $RunnerRoot
try {
    & .\config.cmd --unattended --replace --url "https://github.com/$organization/$repository" --token $registrationToken --name $runnerName --labels $runnerLabels --work _work --runasservice
    if ($LASTEXITCODE -ne 0) {
        throw "Runner configuration failed with exit code $LASTEXITCODE."
    }
} finally {
    Remove-Variable registrationToken -ErrorAction SilentlyContinue
    Pop-Location
}

Set-RunnerServiceVirtualAccount -ServiceName (Get-RunnerServiceName)

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

$serviceName = Get-RunnerServiceName
$service = Get-Service -Name $serviceName
if ($service.Status -ne 'Running') {
    throw "Runner service $serviceName is not running."
}
Write-Host "Windows runner $runnerName is online as least-privilege virtual-account service $serviceName." -ForegroundColor Green

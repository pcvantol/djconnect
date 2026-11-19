# Compatibility wrapper. The canonical onboarding package is ..\onboarding.
& "$PSScriptRoot\..\onboarding\dev_onboarding_windows.ps1" @args
exit $LASTEXITCODE

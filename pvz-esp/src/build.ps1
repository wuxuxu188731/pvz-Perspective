#Requires -Version 5.1
<#
    Builds the PvzEsp overlay skeleton with the .NET Framework 4.x C# compiler.

    This machine has no dotnet SDK, so the legacy csc.exe is used. It only
    supports C# 5 syntax: no string interpolation, no ?. / ?[], no nameof,
    no expression-bodied members, no using static, no tuples.

    Usage (from anywhere):
        powershell -ExecutionPolicy Bypass -File .\build.ps1
#>

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrEmpty($scriptDir)) {
    $scriptDir = (Get-Location).Path
}
$srcDir = $scriptDir
$binDir = [System.IO.Path]::GetFullPath((Join-Path $scriptDir '..\bin'))
$outExe = Join-Path $binDir 'Overlay.exe'
$csc = 'C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe'

if (-not (Test-Path -LiteralPath $binDir)) {
    New-Item -ItemType Directory -Path $binDir | Out-Null
}
if (-not (Test-Path -LiteralPath $csc)) {
    throw "csc.exe not found: $csc"
}

$sources = @(Get-ChildItem -Path (Join-Path $srcDir '*.cs') -File | Sort-Object Name | ForEach-Object { $_.FullName })
if ($sources.Count -eq 0) {
    throw "No .cs sources found in $srcDir"
}

$cscArgs = @(
    '/nologo'
    '/target:winexe'
    '/platform:x86'
    '/optimize+'
    ('/out:' + $outExe)
) + $sources + @(
    '/r:System.dll'
    '/r:System.Drawing.dll'
    '/r:System.Windows.Forms.dll'
)

Write-Host "csc     : $csc"
Write-Host "sources : $($sources.Count)"
foreach ($source in $sources) {
    Write-Host "          $source"
}
Write-Host "out     : $outExe"
Write-Host ''

$buildOutput = @(& $csc $cscArgs 2>&1)
$exitCode = $LASTEXITCODE
foreach ($line in $buildOutput) {
    Write-Host $line
}

if ($exitCode -ne 0) {
    throw "csc failed with exit code $exitCode"
}

$warningLines = @($buildOutput | Where-Object { "$_" -match 'warning [A-Z]+[0-9]+' })
if ($warningLines.Count -gt 0) {
    Write-Warning ("Build produced {0} warning line(s)." -f $warningLines.Count)
}
else {
    Write-Host '0 warning(s)'
}

$info = Get-Item -LiteralPath $outExe
Write-Host ("BUILD OK: {0} ({1} bytes)" -f $info.FullName, $info.Length)

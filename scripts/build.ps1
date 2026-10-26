#Requires -Version 5.1
<#
.SYNOPSIS
    用带 Pillow 的 Python 跑 build_pet_pack.py。

.DESCRIPTION
    优先用 PATH 上的 python；如果它没有 Pillow，就回落到 DSH 自带的 Python 运行时。
    其余参数原样传给 build_pet_pack.py。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\build.ps1 --packs yier --force
    powershell -ExecutionPolicy Bypass -File scripts\build.ps1 --preview-only
#>
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$BuildArgs
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot

function Test-Pillow([string]$Exe) {
    try {
        & $Exe -c "import PIL; print(PIL.__version__)" 2>$null | Out-Null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

$python = $null
$candidates = @()
$pathPython = Get-Command python -ErrorAction SilentlyContinue
if ($pathPython) { $candidates += $pathPython.Source }
$dshPython = Join-Path $env:USERPROFILE '.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
$candidates += $dshPython
$candidates += 'C:\Users\ppj\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'

foreach ($c in $candidates) {
    if ($c -and (Test-Path -LiteralPath $c) -and (Test-Pillow $c)) {
        $python = $c
        break
    }
}
if (-not $python) {
    throw "找不到带 Pillow 的 Python。请 pip install pillow，或设置 PATH。"
}
Write-Host "Python: $python" -ForegroundColor DarkGray
Push-Location $ProjectRoot
try {
    & $python scripts\build_pet_pack.py @BuildArgs
    exit $LASTEXITCODE
} finally {
    Pop-Location
}

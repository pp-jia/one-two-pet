#! /usr/bin/env pwsh
#Requires -Version 5.1
<#
.SYNOPSIS
    从 video\hd\ 的绿幕源视频重新生成 yier-hd 的 5 段透明 WebM。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\build_hd.ps1
    powershell -ExecutionPolicy Bypass -File scripts\build_hd.ps1 -Force
#>
[CmdletBinding()]
param(
    [switch]$Force
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
$candidates += (Join-Path $env:USERPROFILE '.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe')
foreach ($c in $candidates) {
    if ($c -and (Test-Path -LiteralPath $c) -and (Test-Pillow $c)) {
        $python = $c
        break
    }
}
if (-not $python) {
    throw "找不到带 Pillow 的 Python。"
}

$map = @(
    @{ src = '00-idle.mp4';     name = '待机HD';       crop = '330,20,960,710';  height = 270 },
    @{ src = '01-swing.mp4';    name = '荡秋千HD';     crop = '180,0,1000,720';  height = 350 },
    @{ src = '02-headache.mp4'; name = '脑阔疼HD';     crop = '340,30,940,710';  height = 270 },
    @{ src = '03-please.mp4';   name = '拜托球球你HD'; crop = '340,30,940,710';  height = 270 },
    @{ src = '04-skincare.mp4'; name = '护肤HD';       crop = '340,30,940,710';  height = 270 }
)

Push-Location $ProjectRoot
try {
    foreach ($m in $map) {
        $src = Join-Path $ProjectRoot "video\hd\$($m.src)"
        $out = Join-Path $ProjectRoot "pet\yier-hd-animation\$($m.name).webm"
        if (-not (Test-Path -LiteralPath $src)) {
            Write-Host "跳过（源视频不存在）：$($m.src)" -ForegroundColor Yellow
            continue
        }
        if ((Test-Path -LiteralPath $out) -and -not $Force) {
            Write-Host "跳过（已存在，-Force 可覆盖）：$($m.name).webm" -ForegroundColor DarkGray
            continue
        }
        Write-Host "导入 $($m.src) -> $($m.name).webm" -ForegroundColor Cyan
        & $python scripts\import_video.py `
            --input $src `
            --name $m.name `
            --pack yier-hd `
            --crop $m.crop `
            --target-height $m.height `
            --key-mode hsv
        if ($LASTEXITCODE -ne 0) { throw "导入失败：$($m.src)" }
    }
    & $python scripts\check_packs.py
} finally {
    Pop-Location
}

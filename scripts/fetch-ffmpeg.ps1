#Requires -Version 5.1
<#
.SYNOPSIS
    下载一份带 libvpx-vp9 的 ffmpeg 到项目 .tools\ffmpeg.exe。

.DESCRIPTION
    构建动画需要能编码 VP9-alpha 的 ffmpeg。系统里没有时，可以用 npm 的
    ffmpeg-static 取一份（约 80 MB，仅构建需要，不进 pet pack）。
#>
[CmdletBinding()]
param(
    [string]$Destination = ""
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($Destination)) {
    $Destination = Join-Path $ProjectRoot '.tools\ffmpeg.exe'
}
$destDir = Split-Path -Parent $Destination
New-Item -ItemType Directory -Force -Path $destDir | Out-Null

if (Test-Path -LiteralPath $Destination) {
    Write-Host "已存在：$Destination" -ForegroundColor Green
    & $Destination -hide_banner -version | Select-Object -First 1
    return
}

$npm = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npm) {
    throw "找不到 npm。请先安装 Node.js，或手动把 ffmpeg.exe 放进 $destDir。"
}

$tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("otp-ffmpeg-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
try {
    Write-Host "安装 ffmpeg-static 到临时目录…"
    & npm install --no-audit --no-fund --prefix $tmp ffmpeg-static@5.3.0
    if ($LASTEXITCODE -ne 0) { throw "npm install 失败（exit $LASTEXITCODE）" }

    $pkg = Join-Path $tmp 'node_modules\ffmpeg-static'
    $exe = Join-Path $pkg 'ffmpeg.exe'
    if (-not (Test-Path -LiteralPath $exe)) {
        Write-Host "npm 跳过了安装脚本，手动执行 install.js…"
        Push-Location $pkg
        try {
            & node install.js
        } finally {
            Pop-Location
        }
    }
    if (-not (Test-Path -LiteralPath $exe)) {
        throw "没有拿到 ffmpeg.exe。请手动下载 https://github.com/eugeneware/ffmpeg-static/releases 后放到 $destDir。"
    }
    Copy-Item -LiteralPath $exe -Destination $Destination -Force
    Write-Host "完成：$Destination" -ForegroundColor Green
    & $Destination -hide_banner -version | Select-Object -First 1
} finally {
    Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
}

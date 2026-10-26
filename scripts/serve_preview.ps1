#Requires -Version 5.1
<#
.SYNOPSIS
    在本地起一个静态服务器，预览所有动画 / 检查透明背景。
#>
[CmdletBinding()]
param(
    [int]$Port = 8787
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "找不到 python。也可以直接用浏览器打开 previews\index.html（部分浏览器对 file:// 视频有限制）。"
}

Write-Host "预览页：http://127.0.0.1:$Port/previews/index.html" -ForegroundColor Cyan
Write-Host "按 Ctrl+C 退出。"
Push-Location $ProjectRoot
try {
    & python -m http.server $Port --bind 127.0.0.1
} finally {
    Pop-Location
}

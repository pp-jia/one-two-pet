#Requires -Version 5.1
<#
.SYNOPSIS
    安装 / 卸载 一二布布 pet pack 到 dsh-pet。

.DESCRIPTION
    dsh-pet 会扫描 $DSH_HOME\dsh-pet\pet\ 下的 <name>-config.json 与
    <name>-animation\ / <name>-memes\。本脚本只复制本项目 pet\ 下的三组文件，
    不修改 main-config.jsonc，也不碰大肥鱼和其他宠物。

.PARAMETER DshHome
    DSH 数据目录，默认 $env:DSH_HOME，否则 %USERPROFILE%\.dsh。

.PARAMETER Uninstall
    删除 yier / bubu / duo 三组文件（只删这些名字）。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\install.ps1
    powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -Uninstall
#>
[CmdletBinding()]
param(
    [string]$DshHome = "",
    [switch]$Uninstall
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$SourcePet = Join-Path $ProjectRoot 'pet'

if ([string]::IsNullOrWhiteSpace($DshHome)) {
    if (-not [string]::IsNullOrWhiteSpace($env:DSH_HOME)) {
        $DshHome = $env:DSH_HOME
    } else {
        $DshHome = Join-Path $env:USERPROFILE '.dsh'
    }
}

$TargetRoot = Join-Path $DshHome 'dsh-pet'
$TargetPet = Join-Path $TargetRoot 'pet'

$ConfigFiles = @('yier-config.json', 'bubu-config.json', 'duo-config.json')
$DirNames = @(
    'yier-animation', 'bubu-animation', 'duo-animation',
    'yier-memes', 'bubu-memes', 'duo-memes'
)

function Assert-SafeTarget([string]$Path) {
    $full = [System.IO.Path]::GetFullPath($Path)
    $root = [System.IO.Path]::GetFullPath($TargetPet)
    if (-not $full.StartsWith($root + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "拒绝操作：$full 不在 $root 下"
    }
}

if ($Uninstall) {
    if (-not (Test-Path -LiteralPath $TargetPet)) {
        Write-Host "没有找到 $TargetPet，无需卸载。" -ForegroundColor Yellow
        return
    }
    foreach ($name in $ConfigFiles) {
        $p = Join-Path $TargetPet $name
        Assert-SafeTarget $p
        if (Test-Path -LiteralPath $p) {
            Remove-Item -LiteralPath $p -Force
            Write-Host "删除 $name" -ForegroundColor DarkGray
        }
    }
    foreach ($name in $DirNames) {
        $p = Join-Path $TargetPet $name
        Assert-SafeTarget $p
        if (Test-Path -LiteralPath $p) {
            Remove-Item -LiteralPath $p -Recurse -Force
            Write-Host "删除 $name\" -ForegroundColor DarkGray
        }
    }
    Write-Host "`n已卸载一二布布。刷新 DSH 页面或右键宠物 →「重载配置」。" -ForegroundColor Green
    return
}

if (-not (Test-Path -LiteralPath $SourcePet)) {
    throw "找不到源目录：$SourcePet（请在项目根目录运行）"
}
if (-not (Test-Path -LiteralPath (Join-Path $TargetRoot 'main-config.jsonc'))) {
    Write-Host "警告：$TargetRoot\main-config.jsonc 不存在，dsh-pet 可能还没安装。" -ForegroundColor Yellow
    Write-Host "      本 pack 依赖 dsh-pet；仍会先复制文件。" -ForegroundColor Yellow
}

New-Item -ItemType Directory -Force -Path $TargetPet | Out-Null

$copied = 0
foreach ($name in $ConfigFiles) {
    $src = Join-Path $SourcePet $name
    if (Test-Path -LiteralPath $src) {
        Copy-Item -LiteralPath $src -Destination $TargetPet -Force
        $copied++
    }
}
foreach ($name in $DirNames) {
    $src = Join-Path $SourcePet $name
    if (Test-Path -LiteralPath $src) {
        $dst = Join-Path $TargetPet $name
        if (Test-Path -LiteralPath $dst) {
            Remove-Item -LiteralPath $dst -Recurse -Force
        }
        Copy-Item -LiteralPath $src -Destination $TargetPet -Recurse -Force
        $copied++
    }
}

$count = (Get-ChildItem -LiteralPath $TargetPet -Recurse -File | Measure-Object).Count
Write-Host "`n已复制 $copied 项到 $TargetPet（共 $count 个文件）。" -ForegroundColor Green
Write-Host "默认显示：一二（左上） + 布布（右上）；双人同框在 duo-config.json 里把 display 改成 web 即可。"
Write-Host "下一步：刷新 DSH 页面，或右键任意宠物 →「重载配置」。" -ForegroundColor Cyan

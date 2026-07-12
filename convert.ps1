<#
.SYNOPSIS
    GLTF/GLB → FBX 转换器 (PowerShell)
.DESCRIPTION
    使用 Blender 后端将 GLTF/GLB 文件转换为 FBX。
.PARAMETER InputPath
    输入 GLTF/GLB 文件路径
.PARAMETER OutputPath
    输出 FBX 文件路径 (可选,默认与输入同目录同名 .fbx)
.PARAMETER Blender
    Blender 可执行文件路径 (可选,自动检测)
.EXAMPLE
    .\convert.ps1 -InputPath model.glb
.EXAMPLE
    .\convert.ps1 -InputPath scene.gltf -OutputPath scene.fbx
.EXAMPLE
    .\convert.ps1 -InputPath model.glb -Blender "D:\Blender\blender.exe"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$InputPath,

    [Parameter(Position = 1)]
    [string]$OutputPath,

    [string]$Blender,

    [double]$Scale = 1.0,

    [switch]$NoBake,

    [switch]$NoModifiers
)

$ErrorActionPreference = "Stop"

# 解析输入路径
$inputFull = Resolve-Path $InputPath -ErrorAction Stop
$inputExt = [IO.Path]::GetExtension($inputFull).ToLower()
if ($inputExt -notin @(".gltf", ".glb")) {
    Write-Warning "文件后缀为 '$inputExt', 预期 .gltf 或 .glb"
}

# 自动生成输出路径
if (-not $OutputPath) {
    $OutputPath = [IO.Path]::ChangeExtension($inputFull, ".fbx")
}
$outputFull = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath)

# 查找 Blender
if (-not $Blender) {
    $candidates = @(
        "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
        "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe",
        "C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
        "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
        "C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
        "C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
        "C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
        "C:\Program Files\Blender Foundation\Blender 3.5\blender.exe",
        "C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe"
    )

    # 非标准路径 (自定义目录名)
    $customPaths = @(
        "D:\Program Files\blender-4.5.0\blender.exe",
        "C:\Program Files\Blender\blender.exe",
        "D:\Program Files\Blender\blender.exe"
    )
    foreach ($cp in $customPaths) {
        if (Test-Path $cp) { $candidates += $cp }
    }

    $pathBlender = (Get-Command blender.exe -ErrorAction SilentlyContinue).Source
    if ($pathBlender) {
        $candidates = @($pathBlender) + $candidates
    }

    foreach ($c in $candidates) {
        if (Test-Path $c) {
            $Blender = $c
            break
        }
    }
}

if (-not $Blender -or -not (Test-Path $Blender)) {
    Write-Error "未找到 Blender。请安装 Blender (https://www.blender.org/download/) 或通过 -Blender 指定路径。"
    exit 1
}

Write-Host "[信息] Blender: $Blender" -ForegroundColor Cyan
Write-Host "[信息] 输入:   $inputFull" -ForegroundColor Cyan
Write-Host "[信息] 输出:   $outputFull" -ForegroundColor Cyan

# 构建参数
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $scriptDir "gltf2fbx.py"

$extraArgs = @(
    "--input", $inputFull,
    "--output", $outputFull,
    "--scale", $Scale
)
if ($NoBake) { $extraArgs += "--no-bake" }
if ($NoModifiers) { $extraArgs += "--no-modifiers" }

Write-Host "`n[信息] 正在转换..." -ForegroundColor Cyan

$proc = Start-Process -FilePath $Blender `
    -ArgumentList @("--background", "--python", $scriptPath, "--") + $extraArgs `
    -NoNewWindow -PassThru -Wait

if ($proc.ExitCode -eq 0) {
    if (Test-Path $outputFull) {
        $sizeKB = [math]::Round((Get-Item $outputFull).Length / 1KB, 1)
        Write-Host "`n✓ 转换完成!" -ForegroundColor Green
        Write-Host "  输出: $outputFull" -ForegroundColor Green
        Write-Host "  大小: ${sizeKB} KB" -ForegroundColor Green
    } else {
        Write-Error "输出文件未生成"
        exit 1
    }
} else {
    Write-Error "转换失败 (退出码: $($proc.ExitCode))"
    exit $proc.ExitCode
}

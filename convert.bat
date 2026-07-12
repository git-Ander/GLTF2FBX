@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

:: ============================================
:: GLTF to FBX Converter - CMD Wrapper
:: ============================================
:: Usage:
::   convert.bat input.glb
::   convert.bat input.gltf output.fbx
::   convert.bat input.glb output.fbx --blender "D:\Blender\blender.exe"
:: ============================================

set "INPUT="
set "OUTPUT="
set "BLENDER="
set "EXTRA="

:: --- Parse arguments ---
:parse_args
if "%~1"=="" goto :done_parsing
if /i "%~1"=="--blender" (
    set "BLENDER=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--help" goto :show_help
if /i "%~1"=="-h" goto :show_help
if not defined INPUT (
    set "INPUT=%~1"
) else if not defined OUTPUT (
    set "OUTPUT=%~1"
) else (
    set "EXTRA=!EXTRA! %~1"
)
shift
goto :parse_args

:done_parsing

if not defined INPUT (
    echo [ERROR] Please specify an input file
    echo Usage: convert.bat input.glb [output.fbx] [--blender PATH]
    exit /b 1
)

:: --- Find Blender ---
if defined BLENDER goto :found_blender

for %%p in (
    "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
    "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"
    "C:\Program Files\Blender Foundation\Blender 4.3\blender.exe"
    "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
    "C:\Program Files\Blender Foundation\Blender 4.1\blender.exe"
    "C:\Program Files\Blender Foundation\Blender 4.0\blender.exe"
    "C:\Program Files\Blender Foundation\Blender 3.6\blender.exe"
    "D:\Program Files\blender-4.5.0\blender.exe"
) do (
    if exist %%p (
        set "BLENDER=%%~p"
        goto :found_blender
    )
)

where blender.exe >nul 2>&1
if %errorlevel% equ 0 (
    set "BLENDER=blender.exe"
    goto :found_blender
)

echo [ERROR] Blender not found. Please use --blender to specify path
echo Download: https://www.blender.org/download/
exit /b 1

:found_blender
echo [INFO] Blender: %BLENDER%

:: --- Auto-generate output path ---
if not defined OUTPUT (
    set "OUTPUT=%~dpn1.fbx"
)

:: --- Check input ---
if not exist "%INPUT%" (
    echo [ERROR] Input file not found: %INPUT%
    exit /b 1
)

echo [INFO] Input:  %INPUT%
echo [INFO] Output: %OUTPUT%
echo.

:: --- Run conversion ---
"%BLENDER%" --background --python "%~dp0gltf2fbx.py" -- --input "%INPUT%" --output "%OUTPUT%" %EXTRA%

if %errorlevel% equ 0 (
    echo.
    echo ==============================
    echo [OK] Conversion complete!
    echo Output: %OUTPUT%
    echo ==============================
) else (
    echo.
    echo [FAIL] Conversion error. Check logs above.
    exit /b 1
)
exit /b 0

:show_help
echo GLTF to FBX Converter
echo.
echo Usage:
echo   convert.bat input.glb                    :: auto output input.fbx
echo   convert.bat input.gltf output.fbx         :: specify output
echo   convert.bat input.glb --blender "C:\path\to\blender.exe"
echo.
echo Options:
echo   --blender PATH   Path to blender.exe
echo   --help, -h       Show this help
exit /b 0
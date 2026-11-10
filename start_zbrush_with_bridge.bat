@echo off
REM ZBRUSH 2026 ONLY (Python bridge).
REM For ZBrush 2023/2024 use the ZScript bridge: see the README (ZPlugs64 folder).
REM
REM Opens ZBrush 2026 with the bridge already loaded. Maxon documents that
REM Python scripts can be passed on the command line.
REM Set ZBRUSH_EXE to the path of your ZBrush.exe before using.

set "ZBRUSH_EXE=C:\Program Files\Maxon ZBrush 2026\ZBrush.exe"
set "BRIDGE=%~dp0zbrush_bridge\radial_bridge.py"

if not exist "%ZBRUSH_EXE%" (
    echo ZBrush 2026 not found at: %ZBRUSH_EXE%
    echo This .bat is for ZBrush 2026 only. See the README.
    pause
    exit /b 1
)

start "" "%ZBRUSH_EXE%" "%BRIDGE%"

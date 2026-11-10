@echo off
REM SOMENTE ZBRUSH 2026 (ponte em Python).
REM No ZBrush 2023/2024 use a ponte ZScript: veja o README, passo 5 (pasta ZPlugs64).
REM
REM Abre o ZBrush 2026 ja carregando a ponte. A Maxon documenta que scripts
REM Python podem ser passados pela linha de comando.
REM Ajuste ZBRUSH_EXE para o caminho do seu ZBrush.exe antes de usar.

set "ZBRUSH_EXE=C:\Program Files\Maxon ZBrush 2026\ZBrush.exe"
set "BRIDGE=%~dp0zbrush_bridge\radial_bridge.py"

if not exist "%ZBRUSH_EXE%" (
    echo ZBrush 2026 nao encontrado em: %ZBRUSH_EXE%
    echo Este .bat so serve para o ZBrush 2026. Veja o README.
    pause
    exit /b 1
)

start "" "%ZBRUSH_EXE%" "%BRIDGE%"

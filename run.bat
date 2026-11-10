@echo off
cd /d "%~dp0"

REM Na primeira vez: cria o ambiente virtual (.venv) e instala as dependencias.
if not exist ".venv\Scripts\python.exe" (
    echo [radial] Primeira execucao: criando o ambiente virtual em .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [radial] Nao consegui criar o .venv. O Python esta instalado e no PATH?
        pause
        exit /b 1
    )
)

REM Instala as dependencias se ainda faltarem.
".venv\Scripts\python.exe" -c "import PySide6, pynput" 2>nul
if errorlevel 1 (
    echo [radial] Instalando dependencias: PySide6 e pynput ...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [radial] A instalacao falhou. Veja a mensagem acima.
        pause
        exit /b 1
    )
)

echo [radial] Iniciando o menu radial. Feche esta janela para encerrar.
".venv\Scripts\python.exe" -m radial %*
pause

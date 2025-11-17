@echo off
REM Script para iniciar MediaMTX no Windows

setlocal enabledelayedexpansion

echo ===================================
echo   Inicializando MediaMTX
echo ===================================
echo.

REM Verificar se mediamtx.exe existe
if not exist "mediamtx.exe" (
    echo MediaMTX nao encontrado. Fazendo download...
    echo Versao: v1.5.1
    
    REM Download do MediaMTX para Windows 64-bit
    powershell -Command "& {$ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/bluenviron/mediamtx/releases/download/v1.5.1/mediamtx_v1.5.1_windows_amd64.zip' -OutFile 'mediamtx.zip'}"
    
    if errorlevel 1 (
        echo Erro ao fazer download do MediaMTX
        pause
        exit /b 1
    )
    
    echo Extraindo MediaMTX...
    powershell -Command "& {Expand-Archive -Path 'mediamtx.zip' -DestinationPath '.' -Force}"
    del mediamtx.zip
    
    echo MediaMTX baixado com sucesso!
    echo.
)

REM Iniciar MediaMTX
echo Iniciando MediaMTX na porta 8888 (HLS) e 8889 (WHIP)...
echo.

mediamtx.exe config\mediamtx.yml

pause

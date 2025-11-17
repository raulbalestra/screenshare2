@echo off
REM Script simplificado para rodar ScreenShare em um único container no Windows

setlocal enabledelayedexpansion

echo.
echo ╔════════════════════════════════════════════╗
echo ║    ScreenShare All-In-One Docker           ║
echo ╚════════════════════════════════════════════╝
echo.

docker ps >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker nao esta rodando!
    pause
    exit /b 1
)

set MODE=%1
if "%MODE%"=="" set MODE=start

if "%MODE%"=="start" (
    echo 🚀 Iniciando ScreenShare All-In-One...
    docker compose up -d
    echo ✅ Container iniciado!
    
) else if "%MODE%"=="stop" (
    echo ⏹️  Parando ScreenShare...
    docker compose down
    echo ✅ Container parado!
    
) else if "%MODE%"=="build" (
    echo 🔨 Fazendo build da imagem...
    docker compose build --no-cache
    echo ✅ Build concluído!
    
) else if "%MODE%"=="logs" (
    echo 📋 Mostrando logs...
    docker compose logs -f
    
) else if "%MODE%"=="shell" (
    echo 🔧 Abrindo shell do container...
    docker compose exec screenshare bash
    
) else if "%MODE%"=="restart" (
    echo 🔄 Reiniciando...
    docker compose restart
    echo ✅ Container reiniciado!
    
) else (
    echo Uso: %0 [start^|stop^|build^|logs^|shell^|restart]
    echo.
    echo Comandos:
    echo   start               - Iniciar o container
    echo   stop                - Parar o container
    echo   build               - Fazer build da imagem
    echo   logs                - Ver logs em tempo real
    echo   shell               - Abrir bash no container
    echo   restart             - Reiniciar o container
    pause
    exit /b 1
)

echo.
echo 🌐 Endpoints:
echo    API:          http://localhost:8000
echo    HLS:          http://localhost:8888
echo    WHIP:         http://localhost:8889
echo    MediaMTX API: http://localhost:9997
echo    PostgreSQL:   localhost:5432
echo.
pause

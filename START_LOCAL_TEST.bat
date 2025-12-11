@echo off
REM ============================================================
REM Script de Inicialização Rápida - Teste Local com Docker
REM ScreenShare System - Redis Implementation
REM ============================================================

echo.
echo ============================================================
echo   SCREENSHARE - TESTE LOCAL COM DOCKER REDIS
echo ============================================================
echo.

REM Verificar se Docker está instalado
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Docker nao encontrado!
    echo.
    echo Por favor, instale Docker Desktop:
    echo https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)

echo [OK] Docker detectado
echo.

REM Verificar se Docker está rodando
docker ps >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Docker Desktop nao esta rodando!
    echo.
    echo Por favor, inicie Docker Desktop e tente novamente.
    echo.
    pause
    exit /b 1
)

echo [OK] Docker Desktop rodando
echo.

REM Iniciar Redis com Docker Compose
echo ============================================================
echo   PASSO 1: Iniciando Redis com Docker
echo ============================================================
echo.

docker-compose up -d

if errorlevel 1 (
    echo [ERRO] Falha ao iniciar Redis
    pause
    exit /b 1
)

echo.
echo [OK] Redis iniciado com sucesso
echo.
timeout /t 3 >nul

REM Verificar se Redis está respondendo
echo ============================================================
echo   PASSO 2: Testando conexao Redis
echo ============================================================
echo.

docker exec screenshare_redis redis-cli ping >nul 2>&1

if errorlevel 1 (
    echo [ERRO] Redis nao esta respondendo
    echo.
    echo Verificando status do container...
    docker ps | findstr screenshare_redis
    echo.
    pause
    exit /b 1
)

echo [OK] Redis respondendo (PONG)
echo.

REM Instalar dependências Python
echo ============================================================
echo   PASSO 3: Verificando dependencias Python
echo ============================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    pause
    exit /b 1
)

echo [OK] Python detectado
echo.

echo Instalando/Verificando biblioteca redis...
pip install redis==5.0.1 --quiet
echo [OK] Biblioteca redis instalada
echo.

REM Executar testes automatizados
echo ============================================================
echo   PASSO 4: Executando testes automatizados
echo ============================================================
echo.

python test_redis.py

if errorlevel 1 (
    echo.
    echo [ERRO] Alguns testes falharam!
    echo.
    echo Comandos para debug:
    echo   - Ver status: docker-compose ps
    echo   - Ver logs: docker-compose logs redis
    echo   - Reiniciar: docker-compose restart
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   TODOS OS TESTES PASSARAM!
echo ============================================================
echo.
echo Agora voce pode iniciar a aplicacao:
echo.
echo    python app.py
echo.
echo E acessar em:
echo    http://localhost:5000
echo.
echo Comandos uteis:
echo   - Ver logs Redis:     docker-compose logs -f redis
echo   - Parar Redis:        docker-compose stop
echo   - Reiniciar Redis:    docker-compose restart
echo   - Ver stats:          docker exec screenshare_redis redis-cli info stats
echo   - Monitor comandos:   docker exec screenshare_redis redis-cli monitor
echo.

pause

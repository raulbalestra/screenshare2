@echo off
REM Script de Empacotamento para Deploy - Windows
REM ScreenShare - screenshare.itfolkstech.com

echo ========================================
echo    ScreenShare - Empacotamento
echo ========================================
echo.

set TIMESTAMP=%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set OUTPUT=screenshare_deploy_%TIMESTAMP%.tar.gz

echo [INFO] Criando pacote para deploy...
echo.

REM Criar arquivo temporário com lista de arquivos
echo app.py > files.txt
echo security_utils.py >> files.txt
echo setup_db.py >> files.txt
echo requirements.txt >> files.txt
echo runtime.txt >> files.txt
echo .env >> files.txt
echo templates/ >> files.txt
echo sql/ >> files.txt
echo deploy/ >> files.txt

REM Verificar se tar está disponível (Windows 10+)
where tar >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Usando tar nativo do Windows...
    tar -czf %OUTPUT% ^
        app.py ^
        security_utils.py ^
        setup_db.py ^
        requirements.txt ^
        runtime.txt ^
        .env ^
        templates ^
        sql ^
        deploy
    
    if %ERRORLEVEL% EQU 0 (
        echo.
        echo [SUCCESS] Pacote criado: %OUTPUT%
        echo.
        echo ========================================
        echo Proximos passos:
        echo ========================================
        echo 1. Transfira o arquivo %OUTPUT% para o servidor
        echo    usando MobaXterm, WinSCP ou scp:
        echo.
        echo    scp %OUTPUT% root@31.97.156.167:/opt/
        echo.
        echo 2. No servidor, execute:
        echo.
        echo    cd /opt
        echo    tar -xzf %OUTPUT% -C /opt/screenshare/
        echo    cd /opt/screenshare
        echo    chmod +x deploy/deploy.sh
        echo    ./deploy/deploy.sh
        echo.
        echo 3. Configure o arquivo .env com suas senhas
        echo.
        echo 4. Acesse: https://screenshare.itfolkstech.com
        echo ========================================
    ) else (
        echo [ERROR] Falha ao criar pacote
        exit /b 1
    )
) else (
    echo [WARNING] Comando tar nao encontrado
    echo.
    echo Por favor, use uma das opcoes abaixo:
    echo.
    echo 1. Use MobaXterm para transferir os seguintes arquivos:
    echo    - app.py
    echo    - security_utils.py
    echo    - setup_db.py
    echo    - requirements.txt
    echo    - .env
    echo    - pasta templates/
    echo    - pasta sql/
    echo    - pasta deploy/
    echo.
    echo 2. Ou instale Git for Windows que inclui tar:
    echo    https://git-scm.com/download/win
    echo.
)

del files.txt 2>nul

pause

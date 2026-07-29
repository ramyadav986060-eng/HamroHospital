@echo off
setlocal

echo =========================================
echo  Hamro Hospital - One Click Development Run
echo =========================================

REM Move to repository root, then app folder
cd /d "%~dp0"

IF NOT EXIST ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    py -3 -m venv .venv
    IF ERRORLEVEL 1 (
        echo Failed to create virtual environment. Make sure Python is installed.
        pause
        exit /b 1
    )
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing/updating requirements...
python -m pip install --upgrade pip
pip install -r hamro_hospital\requirements.txt
IF ERRORLEVEL 1 (
    echo Failed to install requirements.
    pause
    exit /b 1
)

IF NOT EXIST "hamro_hospital\.env" IF EXIST "hamro_hospital\.env.example" (
    echo Creating local .env from .env.example...
    copy "hamro_hospital\.env.example" "hamro_hospital\.env" >nul
)

cd hamro_hospital

echo Running migrations...
python manage.py migrate
IF ERRORLEVEL 1 (
    echo Migration failed.
    pause
    exit /b 1
)

echo Ensuring demo staff accounts...
python manage.py create_demo_accounts

echo Starting server at http://127.0.0.1:8000/
echo Login: /accounts/login/  Demo password: sashi
echo Press CTRL+C to stop.
python manage.py runserver

endlocal

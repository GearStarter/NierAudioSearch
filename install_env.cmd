@echo off
setlocal

:: Check if virtual environment folder exists
if exist python_embeded (
    echo [INFO] Virtual environment already exists. Skipping setup.
    echo Press any key to exit...
    pause >nul
    exit /b 0
)

echo [INFO] Creating virtual environment...
python -m venv python_embeded
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

:: Activate the virtual environment
call ./python_embeded/Scripts/activate

:: Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

:: Install dependencies (excluding PyTorch)
echo [INFO] Installing standard dependencies...
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [OK] Environment setup complete.
echo Press any key to continue...
pause >nul

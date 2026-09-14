@echo off
setlocal

set "ENV_NAME=course_env"
set "PYTHON_VERSION=3.11"
set "ROOT_DIR=%~dp0.."
set "ROOT_DIR=%ROOT_DIR:\=/%"

echo [INFO] Repository: %ROOT_DIR%
echo [INFO] Environment: %ENV_NAME%
echo [INFO] Python version: %PYTHON_VERSION%

REM ------------------------------------------------------------
REM Поиск conda.bat
REM ------------------------------------------------------------

set "CONDA_BAT="

if defined CONDA_BAT_PATH (
    if exist "%CONDA_BAT_PATH%" (
        set "CONDA_BAT=%CONDA_BAT_PATH%"
    )
)

if not defined CONDA_BAT if exist "%USERPROFILE%\anaconda3\condabin\conda.bat" (
    set "CONDA_BAT=%USERPROFILE%\anaconda3\condabin\conda.bat"
)

if not defined CONDA_BAT if exist "%USERPROFILE%\miniconda3\condabin\conda.bat" (
    set "CONDA_BAT=%USERPROFILE%\miniconda3\condabin\conda.bat"
)

if not defined CONDA_BAT if exist "%ProgramData%\anaconda3\condabin\conda.bat" (
    set "CONDA_BAT=%ProgramData%\anaconda3\condabin\conda.bat"
)

if not defined CONDA_BAT if exist "%ProgramData%\miniconda3\condabin\conda.bat" (
    set "CONDA_BAT=%ProgramData%\miniconda3\condabin\conda.bat"
)

if not defined CONDA_BAT (
    for /f "delims=" %%I in ('where conda.bat 2^>nul') do (
        if not defined CONDA_BAT set "CONDA_BAT=%%I"
    )
)

if not defined CONDA_BAT (
    echo [ERROR] conda.bat was not found.
    echo [ERROR] Install Anaconda or Miniconda, then run this script again.
    exit /b 1
)

echo [OK] Found conda.bat:
echo      %CONDA_BAT%

REM ------------------------------------------------------------
REM Проверка доступности Conda
REM ------------------------------------------------------------

call "%CONDA_BAT%" --version >nul 2>&1

if errorlevel 1 (
    echo [ERROR] Conda is not available.
    exit /b 1
)

REM ------------------------------------------------------------
REM Проверка существования окружения
REM ------------------------------------------------------------

call "%CONDA_BAT%" run -n "%ENV_NAME%" python --version >nul 2>&1

if errorlevel 1 (
    echo [INFO] Environment does not exist. Creating it...
    
    call "%CONDA_BAT%" create -y -n "%ENV_NAME%" python=%PYTHON_VERSION%

    if errorlevel 1 (
        echo [ERROR] Failed to create Conda environment.
        exit /b 1
    )

    echo [OK] Environment created.
) else (
    echo [INFO] Environment already exists. It will not be recreated.
)

REM ------------------------------------------------------------
REM Установка зависимостей через Python конкретного окружения
REM ------------------------------------------------------------

echo [INFO] Installing dependencies from requirements.txt...

call "%CONDA_BAT%" run -n "%ENV_NAME%" python -m pip install --upgrade pip

if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip.
    exit /b 1
)

call "%CONDA_BAT%" run -n "%ENV_NAME%" python -m pip install -r "%ROOT_DIR%/requirements.txt"

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    exit /b 1
)

echo [OK] Dependencies installed.

REM ------------------------------------------------------------
REM Smoke test
REM ------------------------------------------------------------

echo [INFO] Running smoke test...

call "%CONDA_BAT%" run -n "%ENV_NAME%" python "%ROOT_DIR%/broken_env.py"

if errorlevel 1 (
    echo [ERROR] Smoke test failed. Exit code: 1
    exit /b 1
) else (
    echo [OK] Smoke test passed. Exit code: 0
)

echo.
echo [OK] Environment setup completed successfully.
exit /b 0

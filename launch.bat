@echo off
TITLE Aura Audio Suite Launcher

SET VENV_DIR=venv

REM Check if venv exists, if not, create and install
IF NOT EXIST "%VENV_DIR%\Scripts\pip.exe" (
    ECHO.
    ECHO  First-time setup: Creating virtual environment and installing dependencies.
    ECHO  This may take several minutes. Please be patient...
    ECHO.
    python -m venv %VENV_DIR%
    CALL "%VENV_DIR%\Scripts\activate.bat"
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    IF %ERRORLEVEL% NEQ 0 (
        ECHO ERROR: Failed to install dependencies.
        PAUSE
        EXIT /B 1
    )
)

REM Activate the environment
CALL "%VENV_DIR%\Scripts\activate.bat"

ECHO.
ECHO Launching Veritas Audio Suite...
python app.py

ECHO.
ECHO Application closed.
PAUSE
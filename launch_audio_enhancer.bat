@echo off
TITLE Hyper-Efficient Audio Enhancer

REM Set the name of the virtual environment directory
SET VENV_DIR=venv

REM Check if the virtual environment is already set up
IF NOT EXIST "%VENV_DIR%\Scripts\pip.exe" (
    ECHO.
    ECHO  First-time setup: Creating virtual environment and installing libraries.
    ECHO  This may take several minutes depending on your internet connection.
    ECHO  Please be patient...
    ECHO.
    
    REM Create venv
    python -m venv %VENV_DIR%
    
    REM Activate and install
    CALL "%VENV_DIR%\Scripts\activate.bat"
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    
    IF %ERRORLEVEL% NEQ 0 (
        ECHO.
        ECHO **************************************************
        ECHO * ERROR: Failed to install dependencies.
        ECHO * Please check your Python setup and requirements.txt
        ECHO **************************************************
        PAUSE
        EXIT /B 1
    )
)

REM Activate the environment
CALL "%VENV_DIR%\Scripts\activate.bat"

ECHO.
ECHO Launching Audio Enhancer...
python audio_enhancer.py

ECHO.
ECHO Application closed.
PAUSE
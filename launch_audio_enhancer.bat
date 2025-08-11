@echo off
TITLE Audio Enhancer Launcher

REM Set the name of the virtual environment directory
SET VENV_DIR=venv

REM Check if the virtual environment directory exists, create if not
IF NOT EXIST "%VENV_DIR%\Scripts\activate.bat" (
    ECHO Creating virtual environment...
    python -m venv %VENV_DIR%
    ECHO Activating environment and installing dependencies...
    CALL "%VENV_DIR%\Scripts\activate.bat"
    pip install --upgrade pip
    pip install -r requirements.txt
    
    IF %ERRORLEVEL% NEQ 0 (
        ECHO.
        ECHO **************************************************
        ECHO * ERROR: Failed to install dependencies.        *
        ECHO * Please check your Python and network setup.   *
        ECHO **************************************************
        PAUSE
        EXIT /B 1
    )
) ELSE (
    REM If it exists, just activate it
    CALL "%VENV_DIR%\Scripts\activate.bat"
)

ECHO.
ECHO Launching Audio Enhancer Tool...
python audio_enhancer.py

ECHO.
ECHO Application closed.
PAUSE
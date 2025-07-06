@echo off
REM Create and activate virtual environment
python -m venv venv_audio_tool
call venv_audio_tool\Scripts\activate.bat

REM Install dependencies
pip install -r requirements.txt

REM Launch the Python script
python audio_enhancer.py

pause

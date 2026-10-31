@echo off
title Hold to Talk
python -c "import sounddevice, keyboard, pyperclip, openai" 2>nul || python -m pip install -q -r "%~dp0requirements.txt"
python "%~dp0hold_to_talk.py"
pause

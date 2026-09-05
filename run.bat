@echo off
title CineTriage - Sorties Cinema France
echo ===================================================
echo   Lancement de CineTriage (Interface Locale)
echo ===================================================
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\streamlit.exe" run app.py
) else (
    streamlit run app.py
)
pause

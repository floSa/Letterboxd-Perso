@echo off
title Letterboxd-Perso • Mon Letterboxd Personnel
cd /d "%~dp0"
echo ========================================================
echo   Lancement de Letterboxd-Perso (Serveur Ultra-Rapide)
echo   http://localhost:8080
echo ========================================================
start "" "http://localhost:8080"
.\.venv\Scripts\python server.py
pause

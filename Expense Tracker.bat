@echo off
title Expense Tracker
cd /d "%~dp0"
python app.py
if errorlevel 1 pause

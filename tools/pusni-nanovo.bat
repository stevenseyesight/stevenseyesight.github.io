@echo off
chcp 65001 >nul
title Steven's Eyesight - всички снимки наново
echo Проверявам дали е инсталиран Python...
python --version >nul 2>&1
if errorlevel 1 (
  echo.
  echo Python не е намерен. Инсталирай го от python.org/downloads
  echo и сложи отметка "Add python.exe to PATH" при инсталацията.
  pause
  exit /b 1
)
echo Инсталирам/проверявам Pillow...
python -m pip install --quiet pillow
echo.
if "%~1"=="" (
  python "%~dp0build_portfolio.py" --force
) else (
  python "%~dp0build_portfolio.py" --ws "%~1" --force
)
echo.
pause

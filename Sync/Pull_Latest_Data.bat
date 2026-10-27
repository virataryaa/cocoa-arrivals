@echo off
cd /d "%~dp0.."
echo Pulling latest Cocoa data from GitHub into %cd%\Database ...
git pull --rebase
echo.
if errorlevel 1 (echo FAILED - see message above) else (echo Done - local Database folder is up to date)
pause

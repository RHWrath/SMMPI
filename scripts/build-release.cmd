@echo off
REM Wrapper for paths with spaces: run from repo root as scripts\build-release.cmd
setlocal
cd /d "%~dp0.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-release.ps1" %*
exit /b %ERRORLEVEL%

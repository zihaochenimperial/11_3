@echo off
cd /d "%~dp0.."
title Gaussian host pump - create queue\STOP to stop
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0host-pump.ps1" -MaxConcurrent 2
echo Pump exited.
pause

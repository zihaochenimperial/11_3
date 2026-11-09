@echo off
cd /d "%~dp0.."
title Gaussian host pump (loop) - queue\STOP stops, queue\RESTART reloads code
if not exist runs\pump mkdir runs\pump
:loop
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0host-pump.ps1" -MaxConcurrent 2 >> runs\pump\startup.log 2>&1
if exist queue\RESTART (
  del queue\RESTART
  goto loop
)
echo Pump exited. See runs\pump\startup.log if unexpected.
pause

@echo off
echo Cleaning up the fuzzer output folder...
powershell.exe -Command "Remove-Item -Path '.\output\*' -Recurse -Force"
echo --
echo Fuzzer output folder has been reset safely!
pause

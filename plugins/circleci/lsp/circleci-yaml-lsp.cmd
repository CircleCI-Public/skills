@echo off
rem Windows counterpart of circleci-yaml-lsp. Claude Code runs this in its
rem place, since Windows resolves the extensionless command to this file.
rem
rem circleci-yaml-lsp.ps1 finds the version to run, downloads it if need be,
rem and prints the binary's path. Its stdin is NUL and its stdout is captured,
rem so it can't touch the editor's connection. The binary is then started from
rem here, so it gets that connection directly.
setlocal
set "exe="
for /f "usebackq delims=" %%p in (`powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0circleci-yaml-lsp.ps1" ^<NUL`) do set "exe=%%p"
if not defined exe exit /b 1
"%exe%" %*
exit /b %ERRORLEVEL%

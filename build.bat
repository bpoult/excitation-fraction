@echo off
REM Build the standalone Windows app and zip it for distribution.
REM Run from a shell where the project's Python env is active
REM (e.g. Anaconda Prompt: conda activate Ex_Frac_test), then: build.bat
REM Output: dist\ExcitationFraction-win64.zip
setlocal
cd /d "%~dp0"

echo [1/4] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo [2/4] Checking build dependencies...
python -c "import PyInstaller, webview" 2>nul || (
  echo PyInstaller/pywebview not found. Run: pip install -r requirements-build.txt
  exit /b 1
)

echo [3/4] Running PyInstaller...
pyinstaller ExcitationFraction.spec --noconfirm --clean --log-level WARN || exit /b 1

echo [4/4] Zipping dist\ExcitationFraction ...
powershell -NoProfile -Command "Compress-Archive -Path 'dist\ExcitationFraction' -DestinationPath 'dist\ExcitationFraction-win64.zip' -Force" || exit /b 1

for %%F in (dist\ExcitationFraction-win64.zip) do echo Done: %%F (%%~zF bytes)
endlocal

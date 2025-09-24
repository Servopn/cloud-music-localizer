@echo off
echo Starting packaging process...
echo Checking if PyInstaller is installed...
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
)
echo Packaging application...
pyinstaller --noconfirm --onefile --windowed --icon=ml.ico music_manager.py
if exist dist\music_manager.exe (
    echo.
    echo Packaging completed successfully!
    echo Executable location: %cd%\dist\music_manager.exe
) else (
    echo.
    echo Packaging failed! Please check error messages.
)
echo.
echo Packaging process finished.
pause
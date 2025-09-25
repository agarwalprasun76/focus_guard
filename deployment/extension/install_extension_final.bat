@echo off
REM Focus Guard Extension - Final One-Click Installer
REM Uses unpacked extension approach - most reliable method

echo Focus Guard Extension - One-Click Installer
echo ==========================================
echo.
echo This installer uses the most reliable method:
echo - Loads the unpacked extension directly
echo - No registry policies or CRX files needed
echo - Works on any Windows machine
echo - No administrator privileges required
echo.

echo Starting installation...
echo.

REM Run the Python installer
python "%~dp0install_extension_final.py"

if %errorLevel% == 0 (
    echo.
    echo Installation process completed!
) else (
    echo.
    echo Installation encountered issues.
    echo Please follow the manual instructions shown above.
)

echo.
echo Press any key to exit...
pause >nul

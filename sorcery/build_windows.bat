@echo off
REM Construit Sorcery.exe (un seul fichier, sans console) avec PyInstaller.
setlocal
cd /d "%~dp0"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo pygame indisponible, essai avec pygame-ce...
    python -m pip install pygame-ce || goto :error
)
python -m pip install pyinstaller || goto :error

echo === Tests headless ===
set SDL_VIDEODRIVER=dummy
set SDL_AUDIODRIVER=dummy
python main.py --selftest || goto :error
set SDL_VIDEODRIVER=
set SDL_AUDIODRIVER=

echo === PyInstaller ===
python -m PyInstaller --noconfirm --clean --onefile --windowed --name Sorcery ^
    --hidden-import selftest --hidden-import solver main.py || goto :error

echo.
echo OK : dist\Sorcery.exe
exit /b 0

:error
echo ECHEC de la construction.
exit /b 1

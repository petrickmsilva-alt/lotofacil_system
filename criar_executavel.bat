@echo off
echo ============================================
echo  CRIANDO EXECUTAVEL LOTOFACIL IA
echo ============================================
echo.

echo Instalando dependencias...
pip install -r requirements.txt

echo.
echo Criando executavel...
pyinstaller --onefile --add-data "templates;templates" --add-data "static;static" --name "LotoFacilIA" --icon "static/icon.ico" app.py

echo.
echo ============================================
echo  EXECUTAVEL CRIADO EM: dist/LotoFacilIA.exe
echo ============================================
pause
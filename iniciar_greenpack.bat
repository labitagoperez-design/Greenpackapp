@echo off
:: Espera para asegurar red
timeout /t 10 /nobreak > nul

:: Entrar a la carpeta
y:
cd "\Despacho\APP_GREENPACK"

:: Ejecutar. Usamos "start /b" para que corra como proceso de fondo
start /b python -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --browser.gatherUsageStats false
exit
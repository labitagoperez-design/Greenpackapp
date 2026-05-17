import pandas as pd
import sqlite3
import os

def sincronizar_desde_excel(ruta_excel, ruta_bd):
    """
    Lee el Excel de producción en modo lectura (sin bloquearlo)
    y vuelca los datos limpios en una tabla de SQLite.
    """
    # 1. Validar que el archivo realmente exista en la red o disco local
    if not os.path.exists(ruta_excel):
        return False, f"No se encontró el archivo Excel en la ruta: {ruta_excel}"
        
    try:
        # 2. Leer el Excel de forma segura usando openpyxl con data_only=True
        # Esto extrae los valores finales de las fórmulas y no bloquea el archivo
        with open(ruta_excel, "rb") as f:
            df = pd.read_excel(
                f, 
                sheet_name="Produccion", # <--- Cambiá por el nombre exacto de la pestaña de Óscar
                engine="openpyxl"
            )
        
        # 3. Limpieza de datos básica
        # Si Óscar dejó filas vacías abajo o al principio, las limpiamos para no ensuciar la BD
        df = df.dropna(how="all") 
        
        # Opcional: Asegurarnos de que los nombres de las columnas no tengan espacios raros al principio/final
        df.columns = [str(col).strip() for col in df.columns]
        
        # 4. Volcar a la Base de Datos SQLite
        with sqlite3.connect(ruta_bd) as conn:
            # Usamos 'replace' para que borre la tabla vieja y cargue la foto actual del Excel.
            # Si preferís acumular datos históricos, usaríamos 'append'.
            df.to_sql("datos_excel_produccion", conn, if_exists="replace", index=False)
            
        return True, f"¡Sincronización exitosa! Se cargaron {len(df)} filas."
        
    except Exception as e:
        return False, f"Error crítico al procesar el archivo: {str(e)}"
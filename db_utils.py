import sqlite3
import pandas as pd
import streamlit as st

def ejecutar_guardado_inteligente(df, tabla_nombre, db_path='greenpack_v4.db'):
    """
    Función Universal: 
    1. Si la tabla no existe, la crea.
    2. Si la tabla existe pero le faltan columnas nuevas, las agrega (ALTER).
    3. Guarda los datos.
    """
    try:
        conn = sqlite3.connect(db_path)
        
        # --- PASO A: Sincronizar Columnas ---
        try:
            # Intentamos leer la tabla para ver qué columnas tiene
            df_existente = pd.read_sql_query(f"SELECT * FROM {tabla_nombre} LIMIT 1", conn)
            
            # Comparamos las columnas que vienen del formulario con las de la DB
            for columna in df.columns:
                if columna not in df_existente.columns:
                    # Si no existe, la creamos al vuelo
                    conn.execute(f"ALTER TABLE {tabla_nombre} ADD COLUMN '{columna}' TEXT")
                    st.info(f"⚙️ Base de Datos: Columna nueva '{columna}' agregada a {tabla_nombre}.")
        except:
            # Si da error es porque la tabla no existe, no hacemos nada 
            # (Pandas la creará en el paso B)
            pass

        # --- PASO B: Guardar los datos ---
        df.to_sql(tabla_nombre, conn, if_exists='append', index=False)
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"❌ Error en el módulo de base de datos: {e}")
        return False

def leer_datos_tabla(tabla_nombre, fecha_columna=None, fecha_valor=None, db_path='greenpack_v4.db'):
    """Lee datos de cualquier tabla, opcionalmente filtrando por fecha."""
    try:
        conn = sqlite3.connect(db_path)
        query = f"SELECT * FROM {tabla_nombre}"
        if fecha_columna and fecha_valor:
            query += f" WHERE {fecha_columna} = '{fecha_valor}'"
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except:
        return pd.DataFrame() # Devuelve vacío si no existe
import streamlit as st
import pandas as pd
import sqlite3
import glob
import os

def conectar_db():
    return sqlite3.connect('greenpack_v4.db')

def procesar_csvs_automaticos():
    # 1. Buscamos archivos .csv en la carpeta principal
    archivos_csv = glob.glob("*.csv")
    
    # Agregamos 'descarte_campo.csv' a la lista de seguimiento
    nombres_permitidos = ['ingreso dia.csv', 'personal.csv', 'stock playa.csv', 'embalado.csv', 'descarte_campo.csv']
    archivos_a_procesar = [f for f in archivos_csv if f.lower() in nombres_permitidos]
    
    if not archivos_a_procesar:
        return False

    exito = False
    
    # Intentamos cargar primero el descarte por si está presente para el cruce
    df_descarte = None
    if 'descarte_campo.csv' in [f.lower() for f in archivos_a_procesar]:
        try:
            df_descarte = pd.read_csv('descarte_campo.csv', sep=None, encoding='latin-1', engine='python')
            # Normalizamos columnas del descarte
            df_descarte.columns = df_descarte.columns.str.strip().str.lower()
        except:
            pass

    for archivo in archivos_a_procesar:
        try:
            nombre_archivo_lower = archivo.lower()
            
            # 2. Leer archivo (detecta si es ; o ,)
            df = pd.read_csv(archivo, sep=None, encoding='latin-1', engine='python', on_bad_lines='skip')

            # 3. Limpieza de datos
            df = df.dropna(how='all', axis=0).dropna(how='all', axis=1)
            
            # --- LÓGICA ESPECIAL PARA INGRESO DIA + DESCARTE ---
            if nombre_archivo_lower == 'ingreso dia.csv':
                # Mapeamos al formato de 'parte dia'
                df_migrado = pd.DataFrame()
                df_migrado['codigo'] = df['CODIGO']
                df_migrado['finca'] = df['Finca']
                df_migrado['productor'] = df['Produtor']
                df_migrado['up'] = df['UP']
                df_migrado['romaneo'] = df['CANTIDAD']
                df_migrado['color'] = df['COLOR ']
                df_migrado['visual'] = df['VISUAL']
                df_migrado['destino'] = df['DESTINO']
                df_migrado['volcado'] = df['VOLCADO A PROD.']
                df_migrado['calidad'] = df['CALIDAD']
                
                # Cruce con descarte si el dataframe de descarte existe
                if df_descarte is not None and 'codigo' in df_descarte.columns:
                    # Buscamos 'descarte_kg' o la columna que contenga el peso del descarte
                    col_peso = [c for c in df_descarte.columns if 'descarte' in c or 'kg' in c]
                    if col_peso:
                        df_migrado = pd.merge(df_migrado, df_descarte[['codigo', col_peso[0]]], on='codigo', how='left')
                        df_migrado.rename(columns={col_peso[0]: 'descarte_kg'}, inplace=True)
                        df_migrado['descarte_kg'] = df_migrado['descarte_kg'].fillna(0)

                # Guardamos como 'preseleccion' (que es tu tabla de parte dia)
                nombre_tabla = 'preseleccion'
                df = df_migrado
            
            elif nombre_archivo_lower == 'personal.csv':
                nombre_tabla = 'personal_embalado'
            elif nombre_archivo_lower == 'descarte_campo.csv':
                nombre_tabla = 'descarte_campo' # Se guarda también por separado
            else:
                nombre_tabla = nombre_archivo_lower.replace(".csv", "").replace(" ", "_")

            # 5. Guardar en Base de Datos
            with conectar_db() as conn:
                df.to_sql(nombre_tabla, conn, if_exists='replace', index=False)
            
            # 6. Mover a carpeta 'procesados'
            if not os.path.exists('procesados'):
                os.makedirs('procesados')
            
            # También guardamos el CSV físico en procesados para el editor manual
            if nombre_tabla == 'preseleccion':
                df.to_csv(os.path.join('procesados', 'parte dia.csv'), index=False)

            destino = os.path.join('procesados', archivo)
            if os.path.exists(destino):
                os.remove(destino)
            
            os.rename(archivo, destino)
            st.toast(f"✅ {archivo} procesado e integrado.")
            exito = True

        except Exception as e:
            st.error(f"❌ Error con {archivo}: {e}")
    
    return exito

def modulo_importar():
    st.header("📂 Importación de Datos")
    st.info("Buscando archivos: `ingreso dia.csv`, `descarte_campo.csv`, `stock playa.csv`, etc.")
    
    if st.button("🔄 Sincronizar y Unificar Carpeta", use_container_width=True):
        if procesar_csvs_automaticos():
            st.success("✅ Sincronización completa. Datos de ingreso y descarte unificados.")
            st.rerun()
        else:
            st.warning("No se encontraron archivos nuevos para procesar.")
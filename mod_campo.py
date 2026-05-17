import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

# Conexión unificada a la base de datos local
def conectar_db():
    return sqlite3.connect('DatosGreenpack.db', check_same_thread=False)

def vista_control_campo():
    st.title("🍋 Muestra Preselección (Conexión en Vivo)")
    st.write("---")

    FINCAS = [
        "30 ZUCCARDI", "34 ZUCCARDI", "ANTAMAPU", "AVELLANEDA", "CLAUDIA",
        "COLOMBRES", "EL 12", "EL 20", "EL ARANDANO", "EL AZAR", "EL MOLINO",
        "EL NARNAJO", "EL QUINCHO", "EL TAJAMAR", "EL TATA", "EL TRECE",
        "ELVEINTE", "FAMAILLA DUMIT S.A", "GREENPACK", "GREYCO", "LA ARGENTINA",
        "LA ESCONDIDA", "LA LUZ", "LAS MELLIZAS", "LAS TIPAS", "LIMONARES",
        "LOS CEIBOS", "LOS CHICOS", "LOS LAPACHOS", "LOS PORCELES", "LOS TARCOS",
        "MARIA DEL ROSARIO", "MONTE BELLO", "MONTE GRANDE", "RIO LORO",
        "TERRA CITRUS", "YAQUILO"
    ]

    # RUTAS DE RED DEL EXCEL 'CAJAS TERMINADAS'
    ruta_red_cajas = r"Y:\Despacho\APP_GREENPACK\datos_origen\cajas terminadas.xlsx"
    ruta_local_cajas = os.path.join(os.getcwd(), "cajas_terminadas_local.xlsx")
    ruta_desencriptado_cajas = os.path.join(os.getcwd(), "cajas_terminadas_libre.xlsx")

    df_descarte_excel = None
    df_campo_excel = None

    # --- 1. ESCUDO DE RED: COPIA EN CALIENTE ---
    try:
        if os.path.exists(ruta_red_cajas):
            import shutil
            shutil.copy2(ruta_red_cajas, ruta_local_cajas)
    except Exception:
        pass

    # Determinamos cuál es el archivo base para descifrar
    archivo_a_descifrar = ruta_local_cajas if os.path.exists(ruta_local_cajas) else ruta_red_cajas

    # --- 2. DESENCRIPTACIÓN AUTOMÁTICA EN SEGUNDO PLANO (ROCKO1) ---
    if os.path.exists(archivo_a_descifrar):
        with st.spinner("🔄 Desencriptando y sincronizando 'cajas terminadas' en vivo..."):
            try:
                import msoffcrypto
                with open(archivo_a_descifrar, "rb") as f_encrypted:
                    office_file = msoffcrypto.OfficeFile(f_encrypted)
                    office_file.load_key(password="ROCKO1") # Quitamos el candado de Oscar
                    with open(ruta_desencriptado_cajas, "wb") as f_decrypted:
                        office_file.decrypt(f_decrypted)

                # --- 3. LECTURA DE LAS HOJAS SEGURO ---
                if os.path.exists(ruta_desencriptado_cajas):
                    # Leemos la hoja 'Descarte Pre'
                    df_descarte_excel = pd.read_excel(ruta_desencriptado_cajas, sheet_name="Descarte Pre", engine="openpyxl")
                    # Leemos la hoja 'Control de campo'
                    df_campo_excel = pd.read_excel(ruta_desencriptado_cajas, sheet_name="Control de campo", engine="openpyxl")
                    
                    # Limpieza del archivo temporal libre de clave por seguridad
                    try:
                        os.remove(ruta_desencriptado_cajas)
                    except Exception:
                        pass
            except Exception as e:
                st.error(f"❌ Error al abrir o desencriptar el archivo Excel: {e}")
    else:
        st.warning("⚠️ No se detectó el archivo 'cajas terminadas.xlsx' en la red de la planta. Mostrando historial local.")

    # MANTENEMOS EL ESQUELETO EXACTO DE TABS QUE TENÍAS
    tab2, tab1 = st.tabs(["🗑️ Control de Descarte", "🚜 Control de Campo"])

    # ============================================================
    # SECCIÓN 1: CONTROL DE CAMPO
    # ============================================================
    with tab1:
        st.subheader("🚜 Control de Calidad de Campo")
        
        # Sincronizamos los datos del Excel a la tabla de control de campo de SQLite
        if df_campo_excel is not None:
            try:
                df_campo_excel.columns = [str(c).strip().upper() for c in df_campo_excel.columns]
                with conectar_db() as conn:
                    # Guardamos/reemplazamos el espejo para visualización rápida
                    df_campo_excel.to_sql('espejo_control_campo', conn, if_exists='replace', index=False)
            except Exception as e:
                st.caption(f"Aviso de sincronización de campo: {e}")

        # Traemos el historial unificado para mostrar
        df_historial_campo = pd.DataFrame()
        try:
            with conectar_db() as conn:
                df_historial_campo = pd.read_sql_query("SELECT * FROM espejo_control_campo", conn)
        except Exception:
            pass

        if not df_historial_campo.empty:
            st.markdown("### 📋 Registros en Vivo desde 'Control de campo'")
            st.data_editor(df_historial_campo, use_container_width=True, hide_index=True, key="editor_hoja_campo")
        else:
            st.info("ℹ️ No hay registros actuales en la hoja 'Control de campo'.")


    # ============================================================
    # SECCIÓN 2: CONTROL DE DESCARTE
    # ============================================================
    with tab2:
        st.subheader("🗑️ Control de Descarte Muestras")

        # Sincronizamos los datos del Excel a la tabla de descarte pre de SQLite
        if df_descarte_excel is not None:
            try:
                df_descarte_excel.columns = [str(c).strip().upper() for c in df_descarte_excel.columns]
                with conectar_db() as conn:
                    df_descarte_excel.to_sql('espejo_descarte_pre', conn, if_exists='replace', index=False)
            except Exception as e:
                st.caption(f"Aviso de sincronización de descarte: {e}")

        # Mostrar la tabla interactiva de Descarte Pre arriba
        df_historial_descarte = pd.DataFrame()
        try:
            with conectar_db() as conn:
                df_historial_descarte = pd.read_sql_query("SELECT * FROM espejo_descarte_pre", conn)
        except Exception:
            pass

        if not df_historial_descarte.empty:
            st.markdown("### 📋 Registros en Vivo desde 'Descarte Pre'")
            st.data_editor(df_historial_descarte, use_container_width=True, hide_index=True, key="editor_hoja_descarte")
        else:
            st.info("ℹ️ No hay registros actuales en la hoja 'Descarte Pre'.")

        st.divider()

        # MANTENEMOS EL FORMULARIO DE CARGA DE ABAJO IGUAL QUE ANTES
        st.subheader("📥 Cargar Nueva Muestra Manual")
        with st.form("form_muestra_descarte", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)

            with col1:
                fecha_m = st.date_input("Fecha Muestreo", datetime.now())
                hora_m = st.text_input("Hora (HH:MM)", datetime.now().strftime("%H:%M"))
                finca_m = st.selectbox("Finca / Productor", FINCAS)
                guia_m = st.text_input("N° Guía / Remito")

            with col2:
                linea_m = st.selectbox("Línea de Proceso", ["Línea 1", "Línea 2", "Preselección"])
                total_kg_m = st.number_input("Total Kg Lote", min_value=0.0, step=10.0, value=0.0)
                descarte_kg_m = st.number_input("Kg Descarte Encontrado", min_value=0.0, step=1.0, value=0.0)

            with col3:
                # El cálculo del porcentaje se hace automático
                if total_kg_m > 0:
                    porcentaje_calculado = round((descarte_kg_m / total_kg_m) * 100, 2)
                else:
                    porcentaje_calculado = 0.0
                st.metric("Porcentaje Descarte (Auto)", f"{porcentaje_calculado}%")
                
                inspector_m = st.text_input("Inspector de Calidad").upper()
                obs_m = st.text_area("Observaciones Generales")

            if st.form_submit_button("💾 Guardar Nueva Muestra Manual"):
                try:
                    with conectar_db() as conn:
                        conn.execute("""
                            CREATE TABLE IF NOT EXISTS muestras_descarte_manual (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                fecha TEXT, hora TEXT, finca TEXT, guia TEXT,
                                linea TEXT, total_kg REAL, descarte_kg REAL,
                                porcentaje REAL, inspector TEXT, observaciones TEXT
                            )
                        """)
                        conn.execute("""
                            INSERT INTO muestras_descarte_manual 
                            (fecha, hora, finca, guia, linea, total_kg, descarte_kg, porcentaje, inspector, observaciones)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            str(fecha_m), str(hora_m), finca_m, guia_m,
                            linea_m, float(total_kg_m), float(descarte_kg_m),
                            float(porcentaje_calculado), inspector_m, obs_m
                        ))
                        conn.commit()
                    st.success("✅ ¡Muestra manual guardada correctamente en la base de datos local!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al guardar el registro manual: {e}")
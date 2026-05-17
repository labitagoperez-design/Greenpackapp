import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from app import guardar_datos_universal
import os

# --- MOTOR DE INYECCIÓN AUTOMÁTICA (EXCEL DE ÓSCAR A TU SQLITE) ---
CARPETA_AUTOMATICA = "datos_origen"

def conectar_db():
    return sqlite3.connect('greenpack_v4.db')

def encontrar_columna(df, palabras_clave):
    """
    Busca de forma inteligente una columna en el DataFrame sin importar si está 
    en mayúsculas, minúsculas, mezcla o si contiene espacios en blanco.
    """
    columnas_limpias = {str(col).strip().upper(): col for col in df.columns}
    for palabra in palabras_clave:
        palabra_up = palabra.upper()
        # Coincidencia exacta
        if palabra_up in columnas_limpias:
            return columnas_limpias[palabra_up]
        # Coincidencia parcial (por si dice 'PRODUCTORES' o 'KILOS TOTALES')
        for col_up, col_original in columnas_limpias.items():
            if palabra_up in col_up:
                return col_original
    return None

def normalizar_fecha_csv(df, col_fecha):
    """
    Convierte cualquier formato de fecha de los CSV (con barras o guiones)
    a un objeto Datetime real para que no se pierdan datos actuales.
    """
    if col_fecha and col_fecha in df.columns:
        df[col_fecha] = df[col_fecha].astype(str).str.strip()
        for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%y'):
            try:
                df['FECHA_DT'] = pd.to_datetime(df[col_fecha], format=fmt, errors='coerce')
                if not df['FECHA_DT'].isna().all():
                    break
            except:
                continue
        if 'FECHA_DT' not in df.columns or df['FECHA_DT'].isna().all():
            df['FECHA_DT'] = pd.to_datetime(df[col_fecha], errors='coerce')
    return df

def inyectar_datos_oscar_silencioso():
    ruta_excel = os.path.join(CARPETA_AUTOMATICA, "volcado Production 2025.xlsx")
    if not os.path.exists(ruta_excel):
        return

    try:
        with open(ruta_excel, "rb") as f:
            df_excel = pd.read_excel(f, sheet_name="VOLCADO", engine="openpyxl")
        
        df_excel.columns = [str(col).strip().upper() for col in df_excel.columns]
        col_codigo = next((c for c in df_excel.columns if "CODIGO" in c or "BIN" in c), None)
        
        if col_codigo:
            df_excel = df_excel[df_excel[col_codigo].notna()]
            df_excel[col_codigo] = df_excel[col_codigo].astype(str).str.strip()
            df_excel = df_excel[(df_excel[col_codigo] != "") & (df_excel[col_codigo].str.lower() != "nan")]

        col_fecha = next((c for c in df_excel.columns if "FECHA" in c), None)
        col_productor = next((c for c in df_excel.columns if "PRODUCTOR" in c), None)
        col_finca = next((c for c in df_excel.columns if "FINCA" in c), None)
        col_cantidad = next((c for c in df_excel.columns if "CANTIDAD" in c or "BINES" in c), None)

        if col_codigo and not df_excel.empty:
            with conectar_db() as conn:
                existentes = pd.read_sql_query("SELECT codigo FROM control_volcado", conn)
                lista_existentes = existentes['codigo'].astype(str).str.strip().tolist()
                
                meses = {1:"ene", 2:"feb", 3:"mar", 4:"abr", 5:"may", 6:"jun",
                         7:"jul", 8:"ago", 9:"sep", 10:"oct", 11:"nov", 12:"dic"}

                for _, row in df_excel.iterrows():
                    cod_bin = str(row[col_codigo]).replace('.0', '').strip()
                    
                    if cod_bin and cod_bin not in lista_existentes:
                        val_fecha = row[col_fecha] if col_fecha in row else None
                        if isinstance(val_fecha, datetime):
                            dt_obj = val_fecha
                        else:
                            try:
                                dt_obj = pd.to_datetime(str(val_fecha).split()[0])
                                if pd.isna(dt_obj): dt_obj = datetime.now()
                            except:
                                dt_obj = datetime.now()
                        
                        if dt_obj.hour < 7:
                            jornada_dt = dt_obj - timedelta(days=1)
                        else:
                            jornada_dt = dt_obj
                            
                        jornada_formateada = f"{jornada_dt.day}-{meses[jornada_dt.month]}"
                        fecha_registro_str = dt_obj.strftime("%Y-%m-%d %H:%M:%S")

                        turno_val = "1"
                        if 19 <= dt_obj.hour or dt_obj.hour < 7:
                            turno_val = "2"

                        prod_val = str(row[col_productor]).strip().upper() if col_productor and pd.notna(row[col_productor]) else "S/D"
                        finca_val = str(row[col_finca]).strip().upper() if col_finca and pd.notna(row[col_finca]) else "S/D"
                        
                        cant_val = pd.to_numeric(row[col_cantidad], errors='coerce') if col_cantidad else 1
                        if pd.isna(cant_val) or cant_val <= 0: cant_val = 1

                        conn.execute("""
                            INSERT INTO control_volcado (fecha, fecha_produccion, turno, codigo, productor, finca, color, cantidad)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (fecha_registro_str, jornada_formateada, str(turno_val), cod_bin, prod_val, finca_val, "S/D", cant_val))
                conn.commit()
    except Exception:
        pass

def mostrar_produccion(guardar_datos_universal):
    inyectar_datos_oscar_silencioso()

    st.title("⚙️ Control de Producción")
    base_path = os.path.dirname(os.path.abspath(__file__))

    tabs = st.tabs([
        "🚜 Volcado", "👷 Embalado", "🗑️ Descarte", "📦 Cajas",
        "📦 Cajas Terminadas", "🧪 Control Testigo", "📊 Rendimientos", "📑 Panel Resumen"
    ])
    
    tab_vol, tab_emb, tab_des, tab_caj, tab_caj_term, tab_test, tab_rend, tab_resumen = tabs

    ahora = datetime.now()
    fecha_ref = ahora - timedelta(days=1) if ahora.hour < 7 else ahora
    meses = {1:"ene", 2:"feb", 3:"mar", 4:"abr", 5:"may", 6:"jun", 7:"jul", 8:"ago", 9:"sep", 10:"oct", 11:"nov", 12:"dic"}
    jornada_actual_str = f"{fecha_ref.day}-{meses[fecha_ref.month]}"
    turno_sugerido = 1 if 7 <= ahora.hour < 19 else 2

    # ========================================================
    # PESTAÑA 1: VOLCADO
    # ========================================================
    with tab_vol:
        st.subheader("Registro de Volcado")
        conn = conectar_db()
        
        c_time1, c_time2, c_time3 = st.columns(3)
        c_time1.metric("📅 Fecha Producción", fecha_ref.strftime("%d/%m/%Y"))
        c_time2.metric("⌚ Hora Registro", ahora.strftime("%H:%M"))
        t_prod_sel = c_time3.selectbox("⏱️ Seleccionar Turno", [1, 2], index=(turno_sugerido - 1), key="sel_turno_v_final")
        
        st.divider()

        try:
            df_piso = pd.read_sql_query("SELECT * FROM tabla_maestra_final WHERE volcado = 0 OR volcado = '0'", conn)
            if not df_piso.empty:
                df_piso.columns = [str(c).strip() for c in df_piso.columns] 
                lista_codigos = sorted([str(x).replace('.0', '').strip() for x in df_piso['codigo'].unique().tolist() if x])
                cod_sel = st.selectbox("Seleccionar Bin para Volcar", [""] + lista_codigos, key="vol_santi_turno")
                
                if cod_sel != "":
                    busqueda = df_piso[df_piso['codigo'] == cod_sel]
                    if not busqueda.empty:
                        datos = busqueda.iloc[0]
                        cant_real = pd.to_numeric(datos.get('cantidad', 1), errors='coerce') or 1
                        
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Productor", str(datos.get('productor', 'S/D')))
                        m2.metric("Finca", str(datos.get('finca', 'S/D')))
                        m3.metric("Bines", f"{int(cant_real)} Unid.")
                        
                        with st.form("form_volcado_santi"):
                            color_v = st.text_input("Confirmar Color", value=str(datos.get('visual', 'S/D')))
                            if st.form_submit_button("🚀 CONFIRMAR VOLCADO", use_container_width=True):
                                datos_v = {
                                    "fecha": ahora.strftime("%Y-%m-%d %H:%M:%S"),
                                    "fecha_produccion": jornada_actual_str,
                                    "turno": t_prod_sel,
                                    "codigo": cod_sel,
                                    "productor": datos.get('productor', 'S/D'),
                                    "finca": datos.get('finca', 'S/D'),
                                    "color": color_v,
                                    "cantidad": cant_real
                                }
                                if guardar_datos_universal(datos_v, "control_volcado"):
                                    conn.execute("UPDATE tabla_maestra_final SET volcado = 1 WHERE codigo = ?", (cod_sel,))
                                    conn.commit()
                                    st.success(f"Bin {cod_sel} registrado.")
                                    st.rerun()
        except Exception as e:
            st.error(f"Error al cargar stock: {e}")

        st.divider()
        st.subheader("📜 Historial de Volcados")
        
        try:
            df_hist = pd.read_sql_query("SELECT * FROM control_volcado WHERE codigo IS NOT NULL AND codigo != '' AND codigo != 'nan' ORDER BY rowid ASC", conn)
            if not df_hist.empty:
                df_hist['cantidad'] = pd.to_numeric(df_hist['cantidad'], errors='coerce').fillna(0)
                df_hist['turno'] = df_hist['turno'].astype(str).replace(['nan', '0.0', '0'], '1')
                df_hist = df_hist[df_hist['fecha_produccion'].notna() & (df_hist['fecha_produccion'] != "")]
                
                f1, f2, f3 = st.columns(3)
                dias = ["TODOS"] + sorted([str(x) for x in df_hist['fecha_produccion'].unique() if x], reverse=True)
                f_dia = f1.selectbox("📅 Jornada", dias, key="h_f_dia_hist")
                f_turno = f2.selectbox("⏱️ Turno", ["TODOS", "1", "2"], key="h_f_turno_hist")
                f_prod = f3.selectbox("🚜 Productor", ["TODOS"] + sorted([str(x) for x in df_hist['productor'].unique() if x]), key="h_f_prod_hist")

                df_f = df_hist.copy()
                if f_dia != "TODOS": df_f = df_f[df_f['fecha_produccion'] == f_dia]
                if f_turno != "TODOS": df_f = df_f[df_f['turno'] == f_turno]
                if f_prod != "TODOS": df_f = df_f[df_f['productor'] == f_prod]

                st.metric("Total Bines Volcados", f"{int(df_f['cantidad'].sum())} Bins")
                st.dataframe(df_f[['codigo', 'fecha', 'fecha_produccion', 'turno', 'productor', 'cantidad']], use_container_width=True, hide_index=True)
            else:
                st.info("No hay registros en el historial.")
        except Exception as e: st.error(f"Error en historial: {e}")
        conn.close()

# ========================================================
    # PESTAÑA 2: EMBALADO (CALIBRACIÓN DE HORAS NUMÉRICAS REALES)
    # ========================================================
    with tab_emb:
        st.subheader("👷 Planilla de Embalado - Archivo Original")

        ruta_red = r"Y:\Despacho\APP_GREENPACK\datos_origen\volcado Produccion 2025.xlsx"
        ruta_local = os.path.join(os.getcwd(), "volcado_produccion_local.xlsx")
        ruta_desencriptado = os.path.join(os.getcwd(), "volcado_produccion_libre.xlsx")
        PESO_CAJA = 15  # Factor de Kg por caja para el KPI

        df_embalado = None

        # --- 1. COPIA LOCAL EN CALIENTE ---
        try:
            if os.path.exists(ruta_red):
                import shutil
                shutil.copy2(ruta_red, ruta_local)
        except Exception:
            pass

        # --- 2. DESENCRIPTACIÓN CON LA CLAVE ROCKO1 ---
        archivo_bloqueado = ruta_local if os.path.exists(ruta_local) else ruta_red

        if os.path.exists(archivo_bloqueado):
            try:
                import msoffcrypto
                with open(archivo_bloqueado, "rb") as f_encrypted:
                    office_file = msoffcrypto.OfficeFile(f_encrypted)
                    office_file.load_key(password="ROCKO1")
                    
                    with open(ruta_desencriptado, "wb") as f_decrypted:
                        office_file.decrypt(f_decrypted)

                # --- 3. LECTURA DIRECTA DE LA HOJA ---
                if os.path.exists(ruta_desencriptado):
                    df_embalado = pd.read_excel(ruta_desencriptado, sheet_name="EMBALADO", engine="openpyxl")
                    
                    try:
                        os.remove(ruta_desencriptado)
                    except Exception:
                        pass
            except Exception as e:
                st.error(f"❌ Error al abrir/desencriptar el archivo: {e}")

        # --- 4. PROCESAMIENTO ADAPTADO A FORMATOS MIXTOS ---
        if df_embalado is not None:
            try:
                # Normalizamos los nombres de las columnas: pasamos todo a string limpio y en mayúsculas
                # ¡Ojo! Si la columna es el número 1, se convertirá temporalmente a la cadena "1.0" o "1", hay que cuidarlo
                columnas_originales = list(df_embalado.columns)
                nuevas_columnas = []
                
                for c in columnas_originales:
                    c_str = str(c).strip().upper()
                    # Si es un número flotante terminado en .0 (ej: 1.0, 2.0 por el parseo de Excel), lo dejamos como entero limpio
                    if c_str.endswith('.0') and c_str[:-2].isdigit():
                        c_str = c_str[:-2]
                    nuevas_columnas.append(c_str)
                
                df_embalado.columns = nuevas_columnas
                
                # Buscamos de forma flexible Fecha y Turno (para que acepte TURN o TURNO)
                col_fecha = 'FECHA' if 'FECHA' in df_embalado.columns else None
                col_turno = None
                if 'TURN' in df_embalado.columns:
                    col_turno = 'TURN'
                elif 'TURNO' in df_embalado.columns:
                    col_turno = 'TURNO'
                
                if col_fecha and col_turno:
                    # Limpiamos filas sin fecha
                    df_embalado = df_embalado.dropna(subset=[col_fecha])
                    
                    # Convertimos la columna FECHA para poder usar el selector de Streamlit
                    df_embalado['FECHA_FILTRO_INTERNO'] = pd.to_datetime(df_embalado[col_fecha], errors='coerce')
                    
                    nulas_mask = df_embalado['FECHA_FILTRO_INTERNO'].isna()
                    if nulas_mask.any():
                        df_embalado.loc[nulas_mask, 'FECHA_FILTRO_INTERNO'] = pd.to_datetime(
                            df_embalado.loc[nulas_mask, col_fecha].astype(str).str.strip(), 
                            format='%d/%m/%Y', 
                            errors='coerce'
                        )
                    
                    df_embalado = df_embalado.dropna(subset=['FECHA_FILTRO_INTERNO'])
                    
                    if not df_embalado.empty:
                        st.markdown("### 🔍 Filtros de Selección")
                        fe1, fe2 = st.columns(2)
                        
                        fechas_disponibles = sorted(df_embalado['FECHA_FILTRO_INTERNO'].dt.date.unique(), reverse=True)
                        ultima_fecha_emb = df_embalado['FECHA_FILTRO_INTERNO'].max().date()
                        
                        f_fecha_emb = fe1.selectbox(
                            "Filtrar por Fecha", 
                            fechas_disponibles, 
                            index=fechas_disponibles.index(ultima_fecha_emb) if ultima_fecha_emb in fechas_disponibles else 0,
                            format_func=lambda x: x.strftime('%d/%m/%Y'),
                            key="fil_fecha_emb_final_v4"
                        )
                        
                        # Pasamos el turno a entero limpio
                        df_embalado[col_turno] = pd.to_numeric(df_embalado[col_turno], errors='coerce').fillna(0).astype(int)
                        turnos_disponibles = sorted([t for t in df_embalado[col_turno].unique() if t > 0])
                        if not turnos_disponibles:
                            turnos_disponibles = [1]
                            
                        f_turno_emb = fe2.selectbox("Filtrar por Turno", turnos_disponibles, key="fil_turno_emb_final_v4")
                        
                        # --- DETECCIÓN DINÁMICA DE COLUMNAS DE HORAS (1 AL 12) ---
                        # Buscamos tanto "1", "2" como "1.0", "2.0" por las dudas
                        columnas_horas = [str(i) for i in range(1, 13)]
                        cols_presentes_horas = [c for c in columnas_horas if c in df_embalado.columns]
                        
                        # Forzamos a que todas las celdas vacías de producción pasen a ser 0
                        for col in cols_presentes_horas:
                            df_embalado[col] = pd.to_numeric(df_embalado[col], errors='coerce').fillna(0).astype(int)
                        
                        # --- 5. CÁLCULO DE KPIS REALES DEL DÍA ---
                        df_del_dia = df_embalado[df_embalado['FECHA_FILTRO_INTERNO'].dt.date == f_fecha_emb].copy()
                        
                        total_cajas_dia = int(df_del_dia[cols_presentes_horas].sum().sum())
                        total_kilos_dia = total_cajas_dia * PESO_CAJA
                        
                        kpi1, kpi2 = st.columns(2)
                        with kpi1:
                            st.markdown(f"""
                                <div style='background-color: #f8fafc; padding: 18px; border-radius: 10px; border-left: 6px solid #1E3A8A; box-shadow: 2px 2px 6px rgba(0,0,0,0.05);'>
                                    <p style='color: #64748b; font-size: 13px; font-weight: bold; margin: 0;'>📦 TOTAL CAJAS DEL DÍA (TODOS LOS TURNOS)</p>
                                    <h2 style='color: #1e293b; margin: 0;'>{total_cajas_dia:,} Cajas</h2>
                                </div>
                            """, unsafe_allow_html=True)
                        with kpi2:
                            st.markdown(f"""
                                <div style='background-color: #f0fdf4; padding: 18px; border-radius: 10px; border-left: 6px solid #16a34a; box-shadow: 2px 2px 6px rgba(0,0,0,0.05);'>
                                    <p style='color: #166534; font-size: 13px; font-weight: bold; margin: 0;'>⚖️ KILOS TOTALES ESTIMADOS DEL DÍA</p>
                                    <h2 style='color: #14532d; margin: 0;'>{total_kilos_dia:,} Kg</h2>
                                </div>
                            """, unsafe_allow_html=True)
                        
                        # --- 6. TABLA DETALLE DEL TURNO SELECCIONADO (UNIFICADA Y LIMPIA) ---
                        df_emb_filtrado = df_del_dia[df_del_dia[col_turno] == int(f_turno_emb)].copy()
                        
                        if not df_emb_filtrado.empty:
                            # Calculamos el total de cajas por fila sumando las horas 1 al 12
                            df_emb_filtrado['TOTAL_CAJAS'] = df_emb_filtrado[cols_presentes_horas].sum(axis=1).astype(int)
                            
                            # Filtramos dinámicamente las columnas base que existan en el Excel original
                            columnas_base = [c for c in ['NOMBRE', 'APELLIDO', 'PERSONA', 'PERSONAL'] if c in df_emb_filtrado.columns]
                            columnas_finales = [col_fecha, col_turno] + columnas_base + cols_presentes_horas + ['TOTAL_CAJAS']
                            cols_render = [c for c in columnas_finales if c in df_emb_filtrado.columns]
                            
                            df_render = df_emb_filtrado[cols_render].copy()
                            
                            # Damos formato de texto legible DD/MM/AAAA a la columna Fecha
                            df_render[col_fecha] = pd.to_datetime(df_render[col_fecha]).dt.strftime('%d/%m/%Y')
                            
                            # Configuración de visualización prolija para las columnas en Streamlit
                            config_columnas_limpias = {
                                col_fecha: st.column_config.TextColumn("Fecha", disabled=True),
                                col_turno: st.column_config.NumberColumn("Turno", format="%d", disabled=True),
                                "TOTAL_CAJAS": st.column_config.NumberColumn("Total Cajas", format="%d", disabled=True)
                            }
                            
                            # Forzamos formato entero sin decimales para las columnas de horas (1 al 12)
                            for h_col in cols_presentes_horas:
                                config_columnas_limpias[h_col] = st.column_config.NumberColumn(h_col, format="%d")
                            
                            st.markdown(f"#### 📋 Detalle de Producción - Turno {f_turno_emb}")
                            
                            # UNA SOLA LLAMADA: Muestra la tabla unificada con todo el personal junto
                            st.dataframe(
                                df_render,
                                use_container_width=True,
                                hide_index=True,
                                column_config=config_columnas_limpias
                            )
                        else:
                            st.warning(f"⚠️ No hay registros en el archivo para la fecha {f_fecha_emb.strftime('%d/%m/%Y')} en el Turno {f_turno_emb}.")
                    else:
                        st.warning("⚠️ No se encontraron filas procesables con fechas válidas en la hoja.")
                else:
                    st.error(f"❌ Estructura incorrecta. Columnas mapeadas: Fecha={col_fecha}, Turno={col_turno}. Columnas del Excel: {list(df_embalado.columns[:5])}")
            except Exception as e:
                st.error(f"❌ Error en el procesamiento interno: {e}")
        else:
            st.warning(f"⚠️ Esperando lectura del archivo en: {ruta_red}")

    # ========================================================
    # PESTAÑA 3: DESCARTE (SUMARIZADO Y BLINDADO)
    # ========================================================
    with tab_des:
        st.subheader("🗑️ Resumen Acumulado de Descartes")
        ruta_csv_descarte = os.path.join(base_path, "procesados", "descarte.csv")
        
        if os.path.exists(ruta_csv_descarte):
            try:
                df_descarte = pd.read_csv(ruta_csv_descarte, sep=';', encoding='latin-1', engine='python')
                
                c_prod = encontrar_columna(df_descarte, ['PRODUCTOR', 'PROD'])
                c_kilos = encontrar_columna(df_descarte, ['KILOS', 'KG'])

                if c_prod and c_kilos:
                    df_descarte = df_descarte[df_descarte[c_prod].notna() & (df_descarte[c_prod].astype(str).str.strip() != "")]
                    df_descarte[c_kilos] = pd.to_numeric(df_descarte[c_kilos], errors='coerce').fillna(0)
                    
                    # Agrupación robusta sin importar cómo se llamen originalmente en el disco
                    df_resumen = df_descarte.groupby(c_prod, as_index=False)[c_kilos].sum()
                    df_resumen = df_resumen.sort_values(by=c_kilos, ascending=False)
                    
                    if not df_resumen.empty:
                        st.metric("Total Descarte Packing General", f"{df_resumen[c_kilos].sum():,.0f} Kg")
                        
                        config_des = {
                            c_prod: st.column_config.TextColumn("Productor / Exportador"),
                            c_kilos: st.column_config.NumberColumn("Suma Total (Kg)", format="%d")
                        }
                        st.dataframe(df_resumen, use_container_width=True, hide_index=True, column_config=config_des)
                    else:
                        st.info("No hay datos de descarte válidos cargados.")
                else:
                    st.error(f"No se mapearon las columnas de Descarte. Columnas reales: {list(df_descarte.columns)}")
            except Exception as e: st.error(f"Error procesando descarte: {e}")
        else: st.warning("No se encontró descarte.csv")

    # ========================================================
    # PESTAÑA 4: CAJAS (LECTURA DE HOJA CAJAS DEL EXCEL MAESTRO)
    # ========================================================
    with tab_caj:
        st.subheader("📦 Registro de Cajas - Volcado Producción")

        # Usamos exactamente la misma ruta que Embalado
        ruta_red = r"Y:\Despacho\APP_GREENPACK\datos_origen\volcado Produccion 2025.xlsx"
        ruta_local = os.path.join(os.getcwd(), "volcado_produccion_local.xlsx")
        ruta_desencriptado = os.path.join(os.getcwd(), "volcado_produccion_libre.xlsx")

        df_cajas = None

        # --- 1. COPIA LOCAL EN CALIENTE (Para no trabar la red) ---
        try:
            if os.path.exists(ruta_red):
                import shutil
                shutil.copy2(ruta_red, ruta_local)
        except Exception:
            pass

        # --- 2. DESENCRIPTACIÓN CON LA CLAVE ROCKO1 ---
        archivo_bloqueado = ruta_local if os.path.exists(ruta_local) else ruta_red

        if os.path.exists(archivo_bloqueado):
            try:
                import msoffcrypto
                with open(archivo_bloqueado, "rb") as f_encrypted:
                    office_file = msoffcrypto.OfficeFile(f_encrypted)
                    office_file.load_key(password="ROCKO1")
                    
                    with open(ruta_desencriptado, "wb") as f_decrypted:
                        office_file.decrypt(f_decrypted)

                # --- 3. LECTURA APUNTANDO A LA HOJA DE CAJAS ---
                if os.path.exists(ruta_desencriptado):
                    try:
                        # Le apuntamos directo al nombre exacto con la C mayúscula
                        df_cajas = pd.read_excel(ruta_desencriptado, sheet_name="Cajas", engine="openpyxl")
                    except Exception:
                        # Por si las dudas en algún momento cambia, intentamos alternativas
                        try:
                            df_cajas = pd.read_excel(ruta_desencriptado, sheet_name="CAJAS", engine="openpyxl")
                        except Exception:
                            df_cajas = pd.read_excel(ruta_desencriptado, sheet_name="cajas", engine="openpyxl")
                    
                    try:
                        os.remove(ruta_desencriptado)
                    except Exception:
                        pass
            except Exception as e:
                st.error(f"❌ Error al abrir o desencriptar la hoja de cajas: {e}")
        else:
            st.warning(f"⚠️ No se encontró el archivo maestro en la ruta: {ruta_red}")

        # --- 4. PROCESAMIENTO Y VISUALIZACIÓN ---
        if df_cajas is not None:
            try:
                # Pasamos los encabezados a Mayúsculas limpias para evitar errores de tipeo
                df_cajas.columns = [str(c).strip().upper() for c in df_cajas.columns]
                
                # Buscamos si hay columna de fecha para que te muestre lo más nuevo arriba de todo
                col_fecha_cajas = next((c for c in df_cajas.columns if 'FECHA' in c), None)
                
                if col_fecha_cajas:
                    # Parseo seguro de fechas
                    df_cajas['FECHA_ORDEN_INTERNA'] = pd.to_datetime(df_cajas[col_fecha_cajas], errors='coerce')
                    
                    # Forzamos formato regional si falló el automático
                    nulas_mask = df_cajas['FECHA_ORDEN_INTERNA'].isna()
                    if nulas_mask.any():
                        df_cajas.loc[nulas_mask, 'FECHA_ORDEN_INTERNA'] = pd.to_datetime(
                            df_cajas.loc[nulas_mask, col_fecha_cajas].astype(str).str.strip(), 
                            format='%d/%m/%Y', 
                            errors='coerce'
                        )
                    
                    # Limpiamos las filas que no tengan fecha real
                    df_cajas = df_cajas.dropna(subset=['FECHA_ORDEN_INTERNA'])
                    
                    # Ordenamos de la más reciente a la más vieja
                    df_cajas = df_cajas.sort_values(by='FECHA_ORDEN_INTERNA', ascending=False)
                    
                    # Convertimos la fecha visible a formato bien legible DD/MM/AAAA
                    df_cajas[col_fecha_cajas] = df_cajas['FECHA_ORDEN_INTERNA'].dt.strftime('%d/%m/%Y')
                    df_cajas = df_cajas.drop(columns=['FECHA_ORDEN_INTERNA'])

                st.markdown("#### 📋 Listado de Cajas Generadas")
                
                # Mostramos la tabla limpia en la interfaz usando todo el ancho de la pantalla
                st.dataframe(
                    df_cajas,
                    use_container_width=True,
                    hide_index=True
                )
                
            except Exception as e:
                st.error(f"❌ Error al procesar los datos de la hoja cajas: {e}")

# ========================================================
    # PESTAÑA 5: CAJAS TERMINADAS (MÓDULO DE RED BLINDADO)
    # ========================================================
    with tab_caj_term:
        st.subheader("📦 Control de Pallets y Stock de Piso")

        # Apuntamos al archivo específico de red y preparamos el escudo local
        ruta_red_cajas = r"Y:\Despacho\APP_GREENPACK\datos_origen\cajas terminadas.xlsx"
        ruta_local_cajas = os.path.join(os.getcwd(), "cajas_terminadas_local.xlsx")
        ruta_desencriptado_cajas = os.path.join(os.getcwd(), "cajas_terminadas_libre.xlsx")

        df_cajas = None

        # --- 1. ESCUDO DE RED: COPIA EN CALIENTE (Evita cuelgues en planta) ---
        try:
            if os.path.exists(ruta_red_cajas):
                import shutil
                shutil.copy2(ruta_red_cajas, ruta_local_cajas)
        except Exception:
            pass

        # --- 2. DESENCRIPTACIÓN EN MEMORIA CON LA CLAVE ROCKO1 ---
        archivo_bloqueado_cajas = ruta_local_cajas if os.path.exists(ruta_local_cajas) else ruta_red_cajas

        if os.path.exists(archivo_bloqueado_cajas):
            try:
                import msoffcrypto
                with open(archivo_bloqueado_cajas, "rb") as f_encrypted:
                    office_file = msoffcrypto.OfficeFile(f_encrypted)
                    # Forzamos la contraseña maestra
                    office_file.load_key(password="ROCKO1")
                    
                    with open(ruta_desencriptado_cajas, "wb") as f_decrypted:
                        office_file.decrypt(f_decrypted)

                # --- 3. LECTURA APUNTANDO AL NOMBRE EXACTO DE LA HOJA ---
                if os.path.exists(ruta_desencriptado_cajas):
                    try:
                        df_cajas = pd.read_excel(ruta_desencriptado_cajas, sheet_name="Cajas Terminadas", engine="openpyxl")
                    except Exception:
                        try:
                            df_cajas = pd.read_excel(ruta_desencriptado_cajas, sheet_name="CAJAS TERMINADAS", engine="openpyxl")
                        except Exception:
                            df_cajas = pd.read_excel(ruta_desencriptado_cajas, engine="openpyxl") # Primera hoja por defecto
                    
                    # Eliminamos el archivo temporal libre del disco
                    try:
                        os.remove(ruta_desencriptado_cajas)
                    except Exception:
                        pass
            except Exception as e:
                st.error(f"❌ Error al abrir o desencriptar el archivo de cajas: {e}")
        else:
            st.warning(f"⚠️ No se encontró el archivo de cajas en la ruta de red: {ruta_red_cajas}")

        # --- 4. PROCESAMIENTO Y VISUALIZACIÓN EN PANTALLA ---
        if df_cajas is not None:
            try:
                # Normalizamos encabezados a mayúsculas limpias
                df_cajas.columns = [str(c).strip().upper() for c in df_cajas.columns]
                
                # Buscamos de forma flexible si el reporte tiene columna de fecha para ordenar
                col_fecha_cajas = next((c for c in df_cajas.columns if 'FECHA' in c), None)
                
                if col_fecha_cajas:
                    # Parseo seguro de fechas para evitar que Streamlit muestre los nanosegundos locos
                    df_cajas['FECHA_FILTRO_INTERNO'] = pd.to_datetime(df_cajas[col_fecha_cajas], errors='coerce')
                    
                    nulas_mask = df_cajas['FECHA_FILTRO_INTERNO'].isna()
                    if nulas_mask.any():
                        df_cajas.loc[nulas_mask, 'FECHA_FILTRO_INTERNO'] = pd.to_datetime(
                            df_cajas.loc[nulas_mask, col_fecha_cajas].astype(str).str.strip(), 
                            format='%d/%m/%Y', 
                            errors='coerce'
                        )
                    
                    # Limpiamos registros sin fecha válida y ordenamos (lo último arriba de todo)
                    df_cajas = df_cajas.dropna(subset=['FECHA_FILTRO_INTERNO'])
                    df_cajas = df_cajas.sort_values(by='FECHA_FILTRO_INTERNO', ascending=False)
                    
                    # Guardamos la fecha limpia en formato DD/MM/AAAA en la columna original
                    df_cajas[col_fecha_cajas] = df_cajas['FECHA_FILTRO_INTERNO'].dt.strftime('%d/%m/%Y')
                    df_cajas = df_cajas.drop(columns=['FECHA_FILTRO_INTERNO'])

                st.markdown("### 📊 Historial de Cajas y Pallets en Stock")
                
                # Renderizado de la tabla usando todo el ancho de la pantalla
                st.dataframe(
                    df_cajas,
                    use_container_width=True,
                    hide_index=True
                )
                
            except Exception as e:
                st.error(f"❌ Error al procesar los datos de stock: {e}")

    # ========================================================
    # PESTAÑA 6: CONTROL TESTIGO (ARCHIVO ENCRIPTADO EN RED)
    # ========================================================
    with tab_test:
        st.subheader("🧪 Planilla de Seguimiento: Control de Testigo")

        # Apuntamos al archivo maestro de cajas y preparamos copias locales
        ruta_red_cajas = r"Y:\Despacho\APP_GREENPACK\datos_origen\cajas terminadas.xlsx"
        ruta_local_cajas = os.path.join(os.getcwd(), "cajas_terminadas_local.xlsx")
        ruta_desencriptado_cajas = os.path.join(os.getcwd(), "cajas_terminadas_libre.xlsx")

        df_testigo = None

        # --- 1. ESCUDO DE RED: COPIA EN CALIENTE (Antibloqueo) ---
        try:
            if os.path.exists(ruta_red_cajas):
                import shutil
                shutil.copy2(ruta_red_cajas, ruta_local_cajas)
        except Exception:
            pass

        # --- 2. DESENCRIPTACIÓN EN MEMORIA CON LA CLAVE ROCKO1 ---
        archivo_bloqueado_cajas = ruta_local_cajas if os.path.exists(ruta_local_cajas) else ruta_red_cajas

        if os.path.exists(archivo_bloqueado_cajas):
            try:
                import msoffcrypto
                with open(archivo_bloqueado_cajas, "rb") as f_encrypted:
                    office_file = msoffcrypto.OfficeFile(f_encrypted)
                    office_file.load_key(password="ROCKO1")
                    
                    with open(ruta_desencriptado_cajas, "wb") as f_decrypted:
                        office_file.decrypt(f_decrypted)

                # --- 3. LECTURA APUNTANDO A LA HOJA MUESTRA TESTIGOS ---
                if os.path.exists(ruta_desencriptado_cajas):
                    try:
                        # Buscamos exactamente el nombre que me indicaste
                        df_testigo = pd.read_excel(ruta_desencriptado_cajas, sheet_name="MUESTRA TESTIGOS", engine="openpyxl")
                    except Exception:
                        # Salvavidas por si cambia a minúsculas o espacios
                        try:
                            df_testigo = pd.read_excel(ruta_desencriptado_cajas, sheet_name="Muestra Testigos", engine="openpyxl")
                        except Exception:
                            df_testigo = pd.read_excel(ruta_desencriptado_cajas, engine="openpyxl")
                    
                    # Eliminamos el archivo temporal desencriptado
                    try:
                        os.remove(ruta_desencriptado_cajas)
                    except Exception:
                        pass
            except Exception as e:
                st.error(f"❌ Error al abrir o desencriptar el control testigo: {e}")
        else:
            st.warning(f"⚠️ No se encontró el archivo de origen en la ruta: {ruta_red_cajas}")

        # --- 4. PROCESAMIENTO Y EDICIÓN EN INTERFAZ ---
        if df_testigo is not None:
            try:
                # Normalizamos nombres de columnas a Mayúsculas limpias
                df_testigo.columns = [str(c).strip().upper() for c in df_testigo.columns]
                
                # Buscamos de forma dinámica una columna de control (Lote o Bin) para limpiar filas vacías de fondo
                c_lote = next((c for c in df_testigo.columns if 'LOTE' in c or 'BIN' in c), None)
                if c_lote:
                    df_testigo = df_testigo[df_testigo[c_lote].notna() & (df_testigo[c_lote].astype(str).str.strip() != "")]
                
                # Buscamos si tiene columna de fecha para corregir el formato y que no muestre nanosegundos
                col_fecha_test = next((c for c in df_testigo.columns if 'FECHA' in c), None)
                if col_fecha_test:
                    df_testigo['FECHA_FILTRO_INTERNO'] = pd.to_datetime(df_testigo[col_fecha_test], errors='coerce')
                    nulas_mask = df_testigo['FECHA_FILTRO_INTERNO'].isna()
                    if nulas_mask.any():
                        df_testigo.loc[nulas_mask, 'FECHA_FILTRO_INTERNO'] = pd.to_datetime(
                            df_testigo.loc[nulas_mask, col_fecha_test].astype(str).str.strip(), 
                            format='%d/%m/%Y', 
                            errors='coerce'
                        )
                    df_testigo = df_testigo.dropna(subset=['FECHA_FILTRO_INTERNO'])
                    df_testigo = df_testigo.sort_values(by='FECHA_FILTRO_INTERNO', ascending=False)
                    df_testigo[col_fecha_test] = df_testigo['FECHA_FILTRO_INTERNO'].dt.strftime('%d/%m/%Y')
                    df_testigo = df_testigo.drop(columns=['FECHA_FILTRO_INTERNO'])

                st.markdown("### 📋 Seguimiento e Historial de Muestras")
                
                # Mantenemos st.data_editor para que puedas modificar celdas en caliente si te hace falta
                st.data_editor(
                    df_testigo, 
                    use_container_width=True, 
                    hide_index=True, 
                    key="ed_test_v5_final"
                )
                
            except Exception as e:
                st.error(f"❌ Error al procesar los datos de testigos: {e}")

    # ========================================================
    # PESTAÑA 7: RENDIMIENTOS (PROCESAMIENTO SEGURO DE FECHAS)
    # ========================================================
    with tab_rend:
        st.subheader("📊 Control de Rendimientos - Resumen Gerencial")

        # Configuración de rutas usando la ingeniería antibloqueo local
        ruta_red_master = r"Y:\Despacho\APP_GREENPACK\datos_origen\volcado Produccion 2025.xlsx"
        ruta_local_master = os.path.join(os.getcwd(), "volcado_produccion_local.xlsx")
        ruta_desencriptado_master = os.path.join(os.getcwd(), "volcado_produccion_libre.xlsx")

        df_prod = None

        # --- 1. ESCUDO DE RED: COPIA EN CALIENTE ---
        try:
            if os.path.exists(ruta_red_master):
                import shutil
                shutil.copy2(ruta_red_master, ruta_local_master)
        except Exception:
            pass

        # --- 2. DESENCRIPTACIÓN CON LA CLAVE ROCKO1 ---
        archivo_bloqueado = ruta_local_master if os.path.exists(ruta_local_master) else ruta_red_master

        if os.path.exists(archivo_bloqueado):
            try:
                import msoffcrypto
                with open(archivo_bloqueado, "rb") as f_encrypted:
                    office_file = msoffcrypto.OfficeFile(f_encrypted)
                    office_file.load_key(password="ROCKO1")
                    
                    with open(ruta_desencriptado_master, "wb") as f_decrypted:
                        office_file.decrypt(f_decrypted)

                # --- 3. LECTURA APUNTANDO A LA HOJA ESPECÍFICA ---
                if os.path.exists(ruta_desencriptado_master):
                    df_prod = pd.read_excel(ruta_desencriptado_master, sheet_name="Produccion por productor", engine="openpyxl")
                    
                    try:
                        os.remove(ruta_desencriptado_master)
                    except Exception:
                        pass
            except Exception as e:
                st.error(f"❌ Error al abrir o desencriptar los datos de rendimientos: {e}")
        else:
            st.warning(f"⚠️ No se encontró el archivo de origen en: {ruta_red_master}")

        # --- 4. PROCESAMIENTO, NORMALIZACIÓN Y LIMPIEZA DE DATOS ---
        if df_prod is not None:
            try:
                # Eliminamos duplicados base de columnas si existieran
                df_prod = df_prod.loc[:, ~df_prod.columns.duplicated()].copy()
                
                # NORMALIZACIÓN INDUSTRIAL: Forzamos todos los nombres de columnas a MAYÚSCULAS limpias
                df_prod.columns = [str(c).strip().upper() for c in df_prod.columns]
                
                # Mapeo directo y seguro sobre la lista normalizada en mayúsculas
                c_fecha = next((c for c in df_prod.columns if 'FECHA' in c), 'FECHA')
                c_turno = next((c for c in df_prod.columns if 'TURNO' in c), 'TURNO')
                c_prod = next((c for c in df_prod.columns if 'PRODUCTOR' in c or 'PROD' in c), 'PRODUCTOR')
                c_up = next((c for c in df_prod.columns if 'UP' in c), 'UP')
                c_finca = next((c for c in df_prod.columns if 'FINCA' in c), 'FINCA')
                c_empaque = next((c for c in df_prod.columns if 'EMPAQUE' in c or 'KG EMPAQUE' in c), 'KG EMPAQUE')
                c_piso = next((c for c in df_prod.columns if 'PISO' in c or 'KG PISO' in c), 'KG PISO')
                c_volcado = next((c for c in df_prod.columns if 'VOLCADO' in c or 'KG VOLCADO' in c), 'VOLCADO')

                # Aseguramos que existan en el dataframe para que no rompa el script
                for col in [c_fecha, c_turno, c_prod, c_up, c_finca, c_empaque, c_piso, c_volcado]:
                    if col not in df_prod.columns:
                        df_prod[col] = None

                # LIMPIEZA CRÍTICA: Descartamos registros sin productor real para volar errores del Excel
                df_prod = df_prod[df_prod[c_prod].notna() & (df_prod[c_prod].astype(str).str.strip() != "")]
                
                # Conversión segura a tipos de datos numéricos limpios
                df_prod[c_volcado] = pd.to_numeric(df_prod[c_volcado], errors='coerce').fillna(0)
                df_prod[c_empaque] = pd.to_numeric(df_prod[c_empaque], errors='coerce').fillna(0)
                df_prod[c_piso] = pd.to_numeric(df_prod[c_piso], errors='coerce').fillna(0)
                
                # PARSEO DE FECHA SEGURO: Creamos una columna datetime real oculta para ordenar sin crasheos
                df_prod['FECHA_DATETIME_INTERNA'] = pd.to_datetime(df_prod[c_fecha], errors='coerce')
                # Eliminamos las filas donde la fecha sea totalmente ilegible o nula de origen
                df_prod = df_prod.dropna(subset=['FECHA_DATETIME_INTERNA'])
                
                # Ordenamos cronológicamente de la más nueva a la más vieja antes de armar los strings del filtro
                df_prod = df_prod.sort_values(by='FECHA_DATETIME_INTERNA', ascending=False)
                
                # Ahora sí generamos el texto visible en formato DD/MM/AAAA garantizando que sean puros STRINGS
                df_prod[c_fecha] = df_prod['FECHA_DATETIME_INTERNA'].dt.strftime('%d/%m/%Y').astype(str)
                
                # Forzamos recalculación matemática pura en Python
                df_prod['REND_EMPAQUE_CALC'] = (df_prod[c_empaque] / df_prod[c_volcado] * 100).fillna(0).round(2)
                df_prod['REND_COMERCIAL_CALC'] = (((df_prod[c_empaque] + df_prod[c_piso]) / df_prod[c_volcado]) * 100).fillna(0).round(2)
                
                # Corregimos infinitos por divisiones entre cero
                df_prod['REND_EMPAQUE_CALC'] = df_prod['REND_EMPAQUE_CALC'].replace([float('inf'), float('-inf')], 0)
                df_prod['REND_COMERCIAL_CALC'] = df_prod['REND_COMERCIAL_CALC'].replace([float('inf'), float('-inf')], 0)

                # Rellenamos campos vacíos para evitar 'nan' en pantalla
                df_prod[c_finca] = df_prod[c_finca].astype(str).str.strip().replace(['nan', 'None', ''], 'SIN ESPECIFICAR')
                df_prod[c_up] = df_prod[c_up].astype(str).str.strip().replace(['nan', 'None', ''], '-')
                
                # Formateamos el turno a entero y luego a string limpio
                df_prod[c_turno] = pd.to_numeric(df_prod[c_turno], errors='coerce').fillna(1).astype(int).astype(str)

                # --- 5. PANEL DE CONTROL: FILTROS DINÁMICOS CRUZADOS ---
                with st.expander("🔍 PANEL DE FILTROS (Finca / Productor / Fecha)", expanded=True):
                    f1, f2, f3 = st.columns(3)
                    
                    with f1:
                        # Obtenemos lista única sin mezclar tipos
                        lista_fincas = sorted([str(x) for x in df_prod[c_finca].unique() if pd.notna(x)])
                        fincas_sel = st.multiselect("Filtrar por Finca:", lista_fincas, placeholder="Todas las fincas")
                    
                    with f2:
                        df_temp_p = df_prod[df_prod[c_finca].isin(fincas_sel)] if fincas_sel else df_prod
                        lista_prods = sorted([str(x) for x in df_temp_p[c_prod].unique() if pd.notna(x)])
                        prods_sel = st.multiselect("Filtrar por Productor:", lista_prods, placeholder="Todos los productores")
                        
                    with f3:
                        df_temp_f = df_prod
                        if fincas_sel: df_temp_f = df_temp_f[df_temp_f[c_finca].isin(fincas_sel)]
                        if prods_sel: df_temp_f = df_temp_f[df_temp_f[c_prod].isin(prods_sel)]
                        
                        # Al estar pre-ordenado por FECHA_DATETIME_INTERNA, mantenemos ese orden cronológico
                        lista_fechas = []
                        for x in df_temp_f[c_fecha].unique():
                            if pd.notna(x) and str(x).strip() != "":
                                lista_fechas.append(str(x))
                                
                        fechas_sel = st.multiselect("Filtrar por Fecha:", lista_fechas, placeholder="Todas las fechas")

                # --- 6. APLICACIÓN DE LOS FILTROS SELECCIONADOS ---
                df_filtrado = df_prod.copy()
                if fincas_sel:
                    df_filtrado = df_filtrado[df_filtrado[c_finca].isin(fincas_sel)]
                if prods_sel:
                    df_filtrado = df_filtrado[df_filtrado[c_prod].isin(prods_sel)]
                if fechas_sel:
                    df_filtrado = df_filtrado[df_filtrado[c_fecha].isin(fechas_sel)]

                # --- 7. RECALCULO DE KPIS EN BASE AL FILTRO EN PANTALLA ---
                df_con_volcado = df_filtrado[df_filtrado[c_volcado] > 0]
                promedio_empaque = df_con_volcado['REND_EMPAQUE_CALC'].mean() if not df_con_volcado.empty else 0
                promedio_comercial = df_con_volcado['REND_COMERCIAL_CALC'].mean() if not df_con_volcado.empty else 0

                kpi1, kpi2 = st.columns(2)
                with kpi1:
                    st.metric(
                        label="🎯 Rendimiento Empaque Promedio", 
                        value=f"{promedio_empaque:.2f} %"
                    )
                with kpi2:
                    st.metric(
                        label="💼 Rendimiento Comercial Promedio", 
                        value=f"{promedio_comercial:.2f} %"
                    )
                
                st.write("---")
                
                # --- 8. ARMADO DE LA TABLA INTEGRAL Y DEFINITIVA ---
                columnas_vista_final = [
                    c_fecha, c_turno, c_prod, c_up, c_finca, 
                    c_empaque, c_piso, c_volcado, 'REND_EMPAQUE_CALC', 'REND_COMERCIAL_CALC'
                ]
                
                mapeo_nombres_vista = {
                    c_fecha: "Fecha",
                    c_turno: "Turno",
                    c_prod: "Productor",
                    c_up: "UP",
                    c_finca: "Finca",
                    c_empaque: "KG Empaque",
                    c_piso: "KG Piso",
                    c_volcado: "Volcado",
                    'REND_EMPAQUE_CALC': "Rendimiento Empaque (%)",
                    'REND_COMERCIAL_CALC': "Rendimiento Comercial (%)"
                }

                df_vista_rend = df_filtrado[columnas_vista_final].copy()

                st.markdown("#### 📋 Detalle de Producción y Rendimientos Activos")
                
                config_columnas_rend = {
                    "Rendimiento Empaque (%)": st.column_config.NumberColumn("Rend. Empaque", format="%.2f %%"),
                    "Rendimiento Comercial (%)": st.column_config.NumberColumn("Rend. Comercial", format="%.2f %%"),
                    "KG Empaque": st.column_config.NumberColumn("KG Empaque", format="%d"),
                    "KG Piso": st.column_config.NumberColumn("KG Piso", format="%d"),
                    "Volcado": st.column_config.NumberColumn("Volcado", format="%d")
                }

                st.dataframe(
                    df_vista_rend.rename(columns=mapeo_nombres_vista),
                    use_container_width=True,
                    hide_index=True,
                    column_config=config_columnas_rend
                )

            except Exception as e:
                st.error(f"❌ Error al procesar el módulo de rendimientos: {e}")

    # ========================================================
    # PESTAÑA 8: RESUMEN DIARIO (CON CUADRO Y GRÁFICO ANALÍTICO)
    # ========================================================
    with tab_resumen:
        st.subheader("📑 Panel Resumen - Cierre de Turno Diario")

        # RUTA MAESTRA: Archivo unificado en red
        ruta_red_resumen = r"Y:\Despacho\APP_GREENPACK\datos_origen\volcado Produccion 2025.xlsx"
        ruta_local_resumen = os.path.join(os.getcwd(), "resumen_diario_local.xlsx")
        ruta_desencriptado_resumen = os.path.join(os.getcwd(), "resumen_diario_libre.xlsx")

        df_crudo = None

        # --- 1. ESCUDO DE RED: COPIA EN CALIENTE ---
        try:
            if os.path.exists(ruta_red_resumen):
                import shutil
                shutil.copy2(ruta_red_resumen, ruta_local_resumen)
        except Exception:
            pass

        # --- 2. DESENCRIPTACIÓN CON LA CLAVE ROCKO1 ---
        archivo_bloqueado = ruta_local_resumen if os.path.exists(ruta_local_resumen) else ruta_red_resumen

        if os.path.exists(archivo_bloqueado):
            try:
                import msoffcrypto
                with open(archivo_bloqueado, "rb") as f_encrypted:
                    office_file = msoffcrypto.OfficeFile(f_encrypted)
                    office_file.load_key(password="ROCKO1")
                    
                    with open(ruta_desencriptado_resumen, "wb") as f_decrypted:
                        office_file.decrypt(f_decrypted)

                # --- 3. LECTURA APUNTANDO A LA HOJA 'RESUMEN' ---
                if os.path.exists(ruta_desencriptado_resumen):
                    df_crudo = pd.read_excel(ruta_desencriptado_resumen, sheet_name="RESUMEN", header=None, engine="openpyxl")
                    
                    try:
                        os.remove(ruta_desencriptado_resumen)
                    except Exception:
                        pass
            except Exception as e:
                st.error(f"❌ Error al abrir o desencriptar la hoja RESUMEN: {e}")
        else:
            st.warning(f"⚠️ No se encontró el archivo maestro en la ruta de red: {ruta_red_resumen}")

        # --- 4. EXTRACCIÓN QUIRÚRGICA DE LA MATRIZ ---
        if df_crudo is not None:
            try:
                # Captura segura de Fecha (Fila 0, Columna 1) y Turno (Fila 1, Columna 1)
                fecha_valor = str(df_crudo.iloc[0, 1]).split()[0] if df_crudo.shape[0] > 0 else "No especificada"
                turno_valor = str(df_crudo.iloc[1, 1]).strip() if df_crudo.shape[0] > 1 else "1"
                
                try:
                    fecha_valor = pd.to_datetime(fecha_valor).strftime('%d/%m/%Y')
                except Exception:
                    pass

                # Encabezado del reporte en pantalla
                c_inf1, c_inf2 = st.columns(2)
                c_inf1.markdown(f"**📅 Fecha del Parte:** `{fecha_valor}`")
                c_inf2.markdown(f"**⏱️ Turno Activo:** `{turno_valor}`")
                st.write("---")

                # --- 5. BUSQUEDA DINÁMICA DEL CUADRO DE PRODUCTORES ---
                idx_inicio = None
                for i, row in df_crudo.iterrows():
                    fila_str = [str(x).upper() for x in row.values]
                    if any('RENDIMIENTOS POR PRODUCTOR' in f or 'RENDIMIENTO COMERCIAL' in f for f in fila_str):
                        idx_inicio = i + 2
                        break

                if idx_inicio is not None:
                    filas_tabla = []
                    
                    # Leemos el bloque de productores (recorremos las filas)
                    for i in range(idx_inicio, min(idx_inicio + 15, df_crudo.shape[0])):
                        row = df_crudo.iloc[i]
                        
                        # Extraemos las celdas según las columnas exactas del archivo (K, L, M, N -> Índices 10, 11, 12, 13)
                        prod_nom = str(row.iloc[10]).strip() if pd.notna(row.iloc[10]) else ""
                        
                        # Si llegamos al final del cuadro o a los TOTALES, cortamos el bucle
                        if prod_nom in ['TOTALES', 'TOTAL', 'nan', ''] or 'TOTAL' in prod_nom.upper():
                            break
                            
                        # Mapeo y sanitización de KGs
                        kg_volc = pd.to_numeric(row.iloc[11], errors='coerce') if pd.notna(row.iloc[11]) else 0
                        kg_prod = pd.to_numeric(row.iloc[12], errors='coerce') if pd.notna(row.iloc[12]) else 0
                        kg_piso = pd.to_numeric(row.iloc[13], errors='coerce') if pd.notna(row.iloc[13]) else 0
                        
                        # Recálculo matemático para limpiar los #DIV/0! del Excel
                        rend_com = (kg_prod / kg_volc * 100) if kg_volc > 0 else 0.0
                        
                        filas_tabla.append({
                            "Productor": prod_nom,
                            "KG Volcado": float(kg_volc),
                            "KG Producido": float(kg_prod),
                            "KG Pisos": float(kg_piso),
                            "Rendimiento Comercial (%)": round(rend_com, 2)
                        })

                    df_resumen_final = pd.DataFrame(filas_tabla)

                    if not df_resumen_final.empty:
                        # --- 6. TARJETAS DE MÉTRICAS GENERALES DE LA PLANTA ---
                        tot_volcado = df_resumen_final["KG Volcado"].sum()
                        tot_producido = df_resumen_final["KG Producido"].sum()
                        rinde_general = (tot_producido / tot_volcado * 100) if tot_volcado > 0 else 0

                        k1, k2, k3 = st.columns(3)
                        k1.metric("📦 Volcado Total del Lote", f"{tot_volcado:,.0f} kg")
                        k2.metric("🍏 Producido Total Neto", f"{tot_producido:,.0f} kg")
                        k3.metric("📈 Rinde Comercial Turno", f"{rinde_general:.2f} %")

                        st.write("---")
                        
                        # Dividimos la pantalla en dos columnas: Tabla a la izquierda, Gráfico a la derecha
                        col_tabla, col_grafico = st.columns([1.1, 0.9])
                        
                        with col_tabla:
                            st.markdown("#### 📋 Datos de la Matriz")
                            st.dataframe(
                                df_resumen_final,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "KG Volcado": st.column_config.NumberColumn("KG Volcado", format="%d"),
                                    "KG Producido": st.column_config.NumberColumn("KG Producido", format="%d"),
                                    "KG Pisos": st.column_config.NumberColumn("KG Pisos", format="%d"),
                                    "Rendimiento Comercial (%)": st.column_config.NumberColumn("Rend. Comercial", format="%.2f %%")
                                }
                            )
                        
                        with col_grafico:
                            st.markdown("#### 📊 Rendimiento Comercial por Productor")
                            
                            # Filtramos productores que tengan rendimiento mayor a 0 para no ensuciar el gráfico con barras vacías
                            df_graficable = df_resumen_final[df_resumen_final["Rendimiento Comercial (%)"] > 0]
                            
                            if not df_graficable.empty:
                                st.bar_chart(
                                    data=df_graficable,
                                    x="Productor",
                                    y="Rendimiento Comercial (%)",
                                    use_container_width=True
                                )
                            else:
                                st.info("ℹ️ No hay rendimientos activos mayores a 0% en este turno para graficar.")
                    else:
                        st.warning("⚠️ No se pudieron estructurar registros de productores válidos en este turno.")
                else:
                    st.error("❌ No se pudo ubicar la fila del cuadro 'Rendimientos por productor' en la hoja.")

            except Exception as e:
                st.error(f"❌ Error en el procesamiento analítico de la matriz resumen: {e}")
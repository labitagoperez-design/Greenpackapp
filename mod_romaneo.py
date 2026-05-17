import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

# Conexión unificada a la base de datos local
def conectar_db():
    return sqlite3.connect('DatosGreenpack.db', check_same_thread=False)

def vista_romaneo():
    st.title("📊 Romaneo de Calibres (Lectura en Vivo)")
    st.write("---")

    # RUTAS DE RED DEL EXCEL 'ROMANEO CALIBRE'
    ruta_red_romaneo = r"Y:\Despacho\APP_GREENPACK\datos_origen\ROMANEO CALIBRES.xlsx"
    ruta_local_romaneo = os.path.join(os.getcwd(), "romaneo_calibre_local.xlsx")
    ruta_desencriptado_romaneo = os.path.join(os.getcwd(), "romaneo_calibre_libre.xlsx")

    df_excel = None

    # --- 1. ESCUDO DE RED: COPIA EN CALIENTE ---
    try:
        if os.path.exists(ruta_red_romaneo):
            import shutil
            shutil.copy2(ruta_red_romaneo, ruta_local_romaneo)
    except Exception:
        pass

    # Determinamos el archivo base para descifrar
    archivo_a_descifrar = ruta_local_romaneo if os.path.exists(ruta_local_romaneo) else ruta_red_romaneo

    # --- 2. DESENCRIPTACIÓN AUTOMÁTICA EN SEGUNDO PLANO (TEDY) ---
    if os.path.exists(archivo_a_descifrar):
        with st.spinner("🔄 Desencriptando y sincronizando Romaneo de Calibres..."):
            try:
                import msoffcrypto
                with open(archivo_a_descifrar, "rb") as f_encrypted:
                    office_file = msoffcrypto.OfficeFile(f_encrypted)
                    office_file.load_key(password="TEDY") # Quitamos el candado de clave
                    with open(ruta_desencriptado_romaneo, "wb") as f_decrypted:
                        office_file.decrypt(f_decrypted)

                # --- 3. LECTURA DE LA HOJA 'ROMANEO' ---
                if os.path.exists(ruta_desencriptado_romaneo):
                    df_excel = pd.read_excel(ruta_desencriptado_romaneo, sheet_name="romaneo", engine="openpyxl")
                    
                    try:
                        os.remove(ruta_desencriptado_romaneo)
                    except Exception:
                        pass
            except Exception as e:
                st.error(f"❌ Error al abrir o desencriptar el archivo de Romaneo: {e}")
    else:
        st.warning("⚠️ No se detectó el archivo 'romaneo calibre.xlsx' en la red. Mostrando historial local.")

    # --- 4. ACTUALIZACIÓN DE LA BASE DE DATOS SQLITE (ESPEJO) ---
    if df_excel is not None:
        try:
            df_excel.columns = [str(c).strip().upper() for c in df_excel.columns]
            with conectar_db() as conn:
                df_excel.to_sql('espejo_romaneo_calibres', conn, if_exists='replace', index=False)
        except Exception as e:
            st.caption(f"Aviso de sincronización interna: {e}")

    # --- 5. LECTURA DEL HISTORIAL PARA PROCESAMIENTO VISUAL ---
    df = pd.DataFrame()
    try:
        with conectar_db() as conn:
            df = pd.read_sql_query("SELECT * FROM espejo_romaneo_calibres", conn)
    except Exception:
        pass

    # --- 6. PROCESAMIENTO COMPATIBLE ---
    if not df.empty:
        calibres_objetivo = [
            'PRE', '216', '198', '180', '162', '150', '138', 
            '125', '113', '100', '88', '80', '72', '64', 'SOBRE'
        ]
        
        cols_presentes = [c for c in calibres_objetivo if c in df.columns]

        # Limpieza de comas y strings numéricos
        for col in cols_presentes:
            df[col] = df[col].astype(str).str.replace(',', '.').str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

        # Buscamos columna de fecha de forma dinámica
        col_fecha = None
        for c in df.columns:
            if 'FECHA' in c:
                col_fecha = c
                break

        if col_fecha:
            df[col_fecha] = pd.to_datetime(df[col_fecha], errors='coerce')
            df = df.dropna(subset=[col_fecha]).sort_values(by=col_fecha, ascending=False)

        # --- PANEL DE FILTROS ---
        with st.expander("🔍 Filtros de Visualización", expanded=True):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                col_prod = 'PRODUCTOR' if 'PRODUCTOR' in df.columns else (df.columns[1] if len(df.columns) > 1 else df.columns[0])
                df[col_prod] = df[col_prod].astype(str).str.upper().str.strip()
                lista_productores = sorted(df[col_prod].unique())
                prod_sel = st.multiselect("Filtrar por Productor:", lista_productores, placeholder="Todos")
            
            with col_f2:
                if col_fecha and not df[col_fecha].isna().all():
                    min_date = df[col_fecha].min().date()
                    max_date = df[col_fecha].max().date()
                    rango_fecha = st.date_input("Rango de Fechas:", [min_date, max_date])
                else:
                    rango_fecha = None

        # Aplicamos los filtros seleccionados
        df_vis = df.copy()
        if prod_sel:
            df_vis = df_vis[df_vis[col_prod].isin(prod_sel)]
        if rango_fecha and len(rango_fecha) == 2:
            df_vis = df_vis[(df_vis[col_fecha].dt.date >= rango_fecha[0]) & (df_vis[col_fecha].dt.date <= rango_fecha[1])]

        # --- 7. DISEÑO DE INTERFAZ EXACTO ---
        if not df_vis.empty:
            sumas_calibres = df_vis[cols_presentes].sum()
            total_real_calculado = sumas_calibres.sum()
            ultima_fecha = df_vis[col_fecha].max() if col_fecha else None

            # Tu tarjeta destacada original
            st.markdown(f"""
                <div style='background-color: #f8fafc; padding: 20px; border-radius: 12px; 
                            border-left: 6px solid #1e40af; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);'>
                    <p style='margin: 0; font-size: 14px; font-weight: bold; color: #1e40af; text-transform: uppercase; letter-spacing: 0.5px;'>
                        Total Kilos Reales Procesados (Filtro Actual)
                    </p>
                    <h2 style='color: #1e293b; margin: 0;'>{total_real_calculado:,.1f} Kg</h2>
                </div>
            """, unsafe_allow_html=True)

            if total_real_calculado > 0:
                st.subheader("📈 Distribución por Calibre (%)")
                
                # 1. Calculamos los porcentajes puros redondeados a 1 decimal
                porcentajes = (sumas_calibres / total_real_calculado * 100).round(1)
                
                # 2. Ajuste matemático de precisión para forzar el 100.0% exacto
                diferencia = round(100.0 - porcentajes.sum(), 1)
                if diferencia != 0.0:
                    # Le sumamos o restamos la diferencia al calibre que más Kilos tenga
                    calibre_mayor = sumas_calibres.idxmax()
                    porcentajes[calibre_mayor] = round(porcentajes[calibre_mayor] + diferencia, 1)

                df_porc = porcentajes.to_frame().T
                
                # 3. Renderizado final en pantalla con tu degradado azul original
                st.dataframe(
                    df_porc.style.format("{:.1f}%").background_gradient(axis=1, cmap="Blues"), 
                    use_container_width=True
                )
                
                st.bar_chart(porcentajes)
                st.caption(f"Suma verificada: {porcentajes.sum():.1f}% | Basado en última carga: {ultima_fecha.strftime('%d/%m/%Y') if col_fecha else 'N/A'}")
            # Tabla detallada interactiva
            st.markdown("#### 📋 Detalle de Bines en Romaneo")
            df_tabla = df_vis.copy()
            if col_fecha and not df_tabla[col_fecha].isna().all():
                df_tabla[col_fecha] = df_tabla[col_fecha].dt.strftime('%d/%m/%Y')

            st.data_editor(df_tabla, use_container_width=True, hide_index=True, key="tabla_romaneo_detalles")
        else:
            st.warning("⚠️ No hay registros de romaneo que coincidan con los filtros aplicados.")
    else:
        st.info("ℹ️ No hay registros históricos en la tabla de romaneo.")
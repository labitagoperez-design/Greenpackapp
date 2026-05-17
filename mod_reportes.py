import streamlit as st
import pandas as pd
import sqlite3
import io
import os

def vista_exportar_datos():
    st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>📊 Centro de Reportes Operativos</h2>", unsafe_allow_html=True)

    def to_excel(df):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Reporte')
        return output.getvalue()

    path_csv = "procesados/"
    
    t1, t2 = st.tabs(["🏗️ Reportes Producción (CSV/App)", "📦 Reportes Packing"])

    # ==========================================================
    # TAB 1: REPORTES PRODUCCIÓN
    # ==========================================================
    with t1:
        st.subheader("Gestión de Producción y Rendimientos")
        
        # Intentamos cargar el CSV que mencionaste
        file_prod = f"{path_csv}productor por produccion.csv"
        
        if os.path.exists(file_prod):
            try:
                # Usamos skip para evitar errores de columnas malformadas
                df_prod = pd.read_csv(file_prod, sep=None, engine='python', encoding='latin1', on_bad_lines='skip')
                df_prod.columns = [c.strip().lower() for c in df_prod.columns]
                
                st.write("### Rendimiento por Productor")
                st.dataframe(df_prod, use_container_width=True)
                st.download_button("📥 Descargar Rendimiento Productor", to_excel(df_prod), "rendimiento_productor.xlsx")
            except Exception as e:
                st.error(f"Error al procesar el CSV de Producción: {e}")
        else:
            st.warning(f"No se encontró el archivo: {file_prod}")

        st.markdown("---")
        st.write("### Datos de Base de Datos (App)")
        try:
            conn = sqlite3.connect('greenpack_v4.db')
            df_ingresos = pd.read_sql_query("SELECT codigo, fecha, up, finca, productor, cantidad FROM tabla_maestra_final", conn)
            
            if not df_ingresos.empty:
                st.write("**Bines Ingresados (Detalle)**")
                st.dataframe(df_ingresos, use_container_width=True)
                st.download_button("📥 Descargar Detalle Ingresos", to_excel(df_ingresos), "detalle_ingresos_app.xlsx")
            conn.close()
        except Exception as e:
            st.info("No se pudieron cargar datos adicionales de la DB.")

    # ==========================================================
    # TAB 2: REPORTES PACKING (CORREGIDO)
    # ==========================================================
    with t2:
        st.subheader("Reportes de Packing (Desde Archivos CSV)")
        
        file_pre = f"{path_csv}ingreso_preseleccion.CSV"
        
        if os.path.exists(file_pre):
            try:
                # Leemos el CSV completo saltando errores de formato
                df_pre = pd.read_csv(file_pre, sep=None, engine='python', encoding='latin1', on_bad_lines='skip')
                
                # Limpiamos nombres de columnas
                df_pre.columns = [c.strip() for c in df_pre.columns]

                # --- LIMPIEZA DE DATOS CRÍTICOS ---
                # Convertimos 'cantidad' o 'Bins Obtenidos' a número, lo que no sea número se vuelve 0
                for col_num in ['cantidad', 'Bins Obtenidos', 'Bins Volcados', 'Rendimiento']:
                    if col_num in df_pre.columns:
                        df_pre[col_num] = pd.to_numeric(df_pre[col_num], errors='coerce').fillna(0)

                st.write("### 📋 Planilla de Preselección Completa")
                
                # Filtro por Productor
                if 'Productor' in df_pre.columns:
                    productores = ["Todos"] + sorted(df_pre['Productor'].dropna().unique().tolist())
                    sel_prod = st.selectbox("Filtrar por Productor (CSV)", productores)
                    
                    if sel_prod != "Todos":
                        df_mostrar = df_pre[df_pre['Productor'] == sel_prod]
                    else:
                        df_mostrar = df_pre
                else:
                    df_mostrar = df_pre

                # Mostramos la tabla (exactamente como el CSV)
                st.dataframe(df_mostrar, use_container_width=True)

                # --- MÉTRICAS DE VALIDACIÓN ---
                col_res1, col_res2, col_res3 = st.columns(3)
                
                # Usamos nombres exactos del CSV para los cálculos
                if 'Bins Volcados' in df_mostrar.columns:
                    v_total = int(df_mostrar['Bins Volcados'].sum())
                    col_res1.metric("Total Bins Volcados", v_total)
                    
                if 'Bins Obtenidos' in df_mostrar.columns:
                    o_total = int(df_mostrar['Bins Obtenidos'].sum())
                    col_res2.metric("Total Bins Obtenidos", o_total)
                    
                if 'Rendimiento' in df_mostrar.columns:
                    r_promedio = df_mostrar['Rendimiento'].mean()
                    col_res3.metric("Rendimiento Promedio", f"{r_promedio:.2f}%")

                st.markdown("---")
                st.download_button(
                    label="📥 Descargar Reporte Packing (Excel)",
                    data=to_excel(df_mostrar),
                    file_name="reporte_packing_fiel.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            except Exception as e:
                st.error(f"Error al procesar el archivo de Packing: {e}")
        else:
            st.warning(f"No se encontró el archivo {file_pre}")
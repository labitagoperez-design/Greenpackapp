import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

def cargar_datos_gerenciales():
    # Ruta donde el motor deposita el archivo sin contraseña
    ruta_datos = r"Y:\Despacho\APP_GREENPACK\procesados\datos_gerencia.xlsx"
    
    if os.path.exists(ruta_datos):
        try:
            with pd.ExcelFile(ruta_datos, engine='openpyxl') as xls:
                # Buscamos la hoja RESUMEN (ignorando mayúsculas/minúsculas)
                nombre_hoja = next((h for h in xls.sheet_names if "RESUMEN" in h.upper().strip()), None)
                
                if nombre_hoja:
                    # Leemos sin encabezados para capturar celdas específicas (como la fecha en B1)
                    df = pd.read_excel(xls, sheet_name=nombre_hoja, header=None)
                    return df
                else:
                    st.error(f"No se encontró la hoja RESUMEN. Hojas detectadas: {xls.sheet_names}")
        except Exception as e:
            st.error(f"Error técnico al abrir el archivo: {e}")
    return None

def mostrar_dashboard_gerencial():
    # Estilo de Ingeniería Greenpack
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { color: #bef264 !important; font-family: 'monospace'; }
        .stTabs [data-baseweb="tab-list"] { gap: 24px; }
        .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #1e293b; border-radius: 4px 4px 0px 0px; color: white; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 style='text-align: center; color: #bef264;'>GREENPACK INTELLIGENCE</h1>", unsafe_allow_html=True)
    
    df = cargar_datos_gerenciales()
    
    if df is not None:
        try:
            # ==========================================
            # EXTRACCIÓN DE DATOS DESDE EL EXCEL DE OSCAR
            # ==========================================
            # Según tu archivo: Fila 0, Col 1 es Fecha | Fila 1, Col 1 es Turno
            fecha_archivo = df.iat[0, 1]
            turno_archivo = df.iat[1, 1]
            
            # Métricas de la Fila 5 del Excel (Índice 4 en Python)
            kg_totales = df.iat[4, 11]       # Columna L (KG)
            kg_comercial = df.iat[4, 12]     # Columna M (Kg Comercial)
            rend_empaque = df.iat[4, 13]     # Columna N (Rendimiento Empaque)
            rend_comercial = df.iat[4, 14]   # Columna O (Rendimiento Comercial %)

            # Mostramos la fecha real del reporte (No la de hoy)
            st.info(f"📊 **REPORTE DE PLANILLA:** {fecha_archivo} | **TURNO:** {turno_archivo}")

            # Tabs de navegación
            tab1, tab2, tab3 = st.tabs(["🚀 NAVE 1: RENDIMIENTO", "📋 NAVE 2: RESUMEN", "⏱️ NAVE 3: TIEMPOS"])

            # ==========================================
            # NAVE 1: RENDIMIENTO
            # ==========================================
            with tab1:
                c1, c2, c3 = st.columns(3)
                c1.metric("KG PRODUCIDOS", f"{kg_totales:,.0f}")
                
                # Convertimos rendimientos a porcentaje legible
                rend_e_val = float(rend_empaque) if float(rend_empaque) > 1 else float(rend_empaque) * 100
                rend_c_val = float(rend_comercial) if float(rend_comercial) > 1 else float(rend_comercial) * 100
                
                c2.metric("REND. EMPAQUE", f"{rend_e_val:.2f}%")
                c3.metric("REND. COMERCIAL", f"{rend_c_val:.2f}%")

                # Gráfico de Gauge para el Rendimiento
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = rend_c_val,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "Eficiencia Comercial", 'font': {'color': "#bef264"}},
                    gauge = {
                        'axis': {'range': [None, 100], 'tickcolor': "white"},
                        'bar': {'color': "#bef264"},
                        'steps': [
                            {'range': [0, 70], 'color': "#334155"},
                            {'range': [70, 85], 'color': "#475569"}],
                    }
                ))
                fig_gauge.update_layout(paper_bgcolor="#0f172a", font={'color': "white"})
                st.plotly_chart(fig_gauge, use_container_width=True)

            # ==========================================
            # NAVE 2: RESUMEN (Calco Pág. 10 PDF)
            # ==========================================
            with tab2:
                st.subheader("Resumen de Producción por Productor")
                
                # Extraemos la tabla de productores que Oscar tiene abajo
                # En tu CSV de ejemplo, los datos reales empiezan en la fila 8 (índice 7)
                try:
                    df_prod = df.iloc[8:12, [10, 11, 12, 14]] # Tomamos Productor, Volcado, Producido y %
                    df_prod.columns = ["Productor", "Kg Volcado", "Kg Producido", "% Rendimiento"]
                    
                    st.dataframe(df_prod.style.format({
                        "Kg Volcado": "{:,.0f}",
                        "Kg Producido": "{:,.0f}",
                        "% Rendimiento": "{:.2f}%"
                    }), use_container_width=True)
                except:
                    st.warning("No se pudo cargar la tabla de productores. Verifica la estructura en el Excel.")

            # ==========================================
            # NAVE 3: TIEMPOS
            # ==========================================
            with tab3:
                st.subheader("Análisis de Tiempos")
                st.write("Datos sincronizados con la hoja de Oscar.")
                # Aquí podrías mapear las horas trabajadas si Oscar las pone en el Excel
                
        except Exception as e:
            st.error(f"Error al procesar las celdas del Excel: {e}")
            st.info("Asegúrate de que Oscar no haya movido las celdas principales en la hoja RESUMEN.")
    else:
        st.warning("⚠️ Esperando que el motor sincronice el archivo 'datos_gerencia.xlsx'...")

if __name__ == "__main__":
    mostrar_dashboard_gerencial()
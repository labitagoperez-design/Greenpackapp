import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

def mostrar_dashboard_gerencial():
    # --- 0. SEGURIDAD ---
    if st.session_state.get('user_actual') != "santi_juarez":
        st.error("No tienes permisos para acceder a este módulo.")
        return

    st.title("📊 Panel de Control Gerencial - Greenpack")

    # --- 1. SIMULACIÓN DE ALERTAS (Lógica de advertencias) ---
    eficiencia_simulada = 68  # Cambia esto para ver cómo cambian los colores
    
    if eficiencia_simulada < 70:
        st.warning(f"⚠️ ALERTA DE PRODUCTIVIDAD: Eficiencia actual del {eficiencia_simulada}% (Bajo el umbral del 70%)")
    
    # --- 2. FILTROS SUPERIORES ---
    with st.expander("🔍 Filtros de Visualización", expanded=False):
        col1, col2, col3 = st.columns(3)
        fecha = col1.date_input("Fecha", datetime.now())
        turno = col2.selectbox("Turno", ["Mañana", "Tarde", "Noche"])
        actualizar = col3.button("🔄 Actualizar Datos")

    # --- 3. PESTAÑAS (TABS) POR SECTOR ---
    tab1, tab2 = st.tabs(["🏗️ SECTOR PRESELECCIÓN", "📦 SECTOR EMPAQUE"])

    with tab1:
        # KPIs Superiores
        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.metric("Bines / Hora", "14.2", "1.5")
        with kpi2:
            st.metric("Kg Ingresados", "52,400", "+5%")
        with kpi3:
            st.metric("Personal Activo", "12 Pers.", "0")

        st.markdown("---")
        
        # Gráficos de Preselección
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.subheader("Distribución por Color")
            # Simulamos datos de tu columna 'visual'
            df_color = pd.DataFrame({
                "Color": ["VO", "V", "VC", "P"],
                "Cantidad": [45, 30, 15, 10]
            })
            fig_pie = px.pie(df_color, values='Cantidad', names='Color', 
                             color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_g2:
            st.subheader("Tiempo Perdido por Paradas")
            df_paradas = pd.DataFrame({
                "Motivo": ["Mecánico", "Eléctrico", "Falta Fruta", "Limpieza"],
                "Minutos": [45, 15, 120, 30]
            })
            fig_bar = px.bar(df_paradas, x='Motivo', y='Minutos', color='Motivo')
            st.plotly_chart(fig_bar, use_container_width=True)

    with tab2:
        # KPIs Superiores
        kpi4, kpi5, kpi6 = st.columns(3)
        with kpi4:
            # Color dinámico para eficiencia
            color_ef = "normal" if eficiencia_simulada > 70 else "inverse"
            st.metric("Eficiencia Operativa", f"{eficiencia_simulada}%", "-4%", delta_color=color_ef)
        with kpi5:
            st.metric("Kg Embalados", "38,200 Kg")
        with kpi6:
            st.metric("Ratio Conversión", "73%", "PROMEDIO")

        st.markdown("---")

        # Gráficos de Empaque
        col_g3, col_g4 = st.columns(2)

        with col_g3:
            st.subheader("Formato de Cajas (Kg)")
            df_cajas = pd.DataFrame({
                "Formato": ["Caja 15kg", "Caja 18kg"],
                "Kilos": [15000, 23200]
            })
            fig_cajas = px.bar(df_cajas, x='Formato', y='Kilos', color='Formato', text_auto=True)
            st.plotly_chart(fig_cajas, use_container_width=True)

        with col_g4:
            st.subheader("Origen de Producción")
            df_origen = pd.DataFrame({
                "Sector": ["Embaladora", "Cajonera"],
                "Cajas": [850, 420]
            })
            fig_col = px.bar(df_origen, y='Sector', x='Cajas', orientation='h', color='Sector')
            st.plotly_chart(fig_col, use_container_width=True)

    # --- 4. PIE DE PÁGINA DE ACTUALIZACIÓN ---
    st.markdown(f"""
        <div style='text-align:right; color:gray;'>
            <small>Última actualización: {datetime.now().strftime('%H:%M:%S')}</small>
        </div>
    """, unsafe_allow_html=True)

# Ejecutar la función
mostrar_dashboard_gerencial()
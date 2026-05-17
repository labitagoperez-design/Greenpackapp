import streamlit as st
import pandas as pd
import sqlite3
import io
from datetime import datetime

def conectar_db():
    return sqlite3.connect('greenpack_v5.db')

def inicializar_db():
    with conectar_db() as conn:
        # Tabla maestra organizada por proceso y turno
        conn.execute("""
            CREATE TABLE IF NOT EXISTS personal_maestro (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proceso TEXT, 
                turno TEXT, 
                puesto TEXT, 
                nombre TEXT, 
                apellido TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS asistencia_diaria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT, operario TEXT, puesto TEXT, proceso TEXT, 
                turno TEXT, entrada TEXT, salida TEXT, horas REAL, estado TEXT
            )
        """)

def calcular_horas_dinamico(h_ent, h_sal):
    try:
        fmt = '%H:%M'
        inicio = datetime.strptime(str(h_ent).strip()[:5], fmt)
        fin = datetime.strptime(str(h_sal).strip()[:5], fmt)
        dif = fin - inicio
        hs = dif.total_seconds() / 3600
        return round(hs if hs >= 0 else hs + 24, 2)
    except: return 0.0

def mostrar_personal():
    inicializar_db()
    st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>👥 Gestión de Personal</h2>", unsafe_allow_html=True)
    
    tabs = st.tabs(["📝 Asistencia", "📊 Historial", "📥 Configuración de Nóminas"])

    with tabs[0]: # ASISTENCIA
        # --- SELECTORES DE ASISTENCIA ---
        c1, c2, c3 = st.columns(3)
        fecha_dt = c1.date_input("Fecha de Asistencia", datetime.now())
        p_asist = c2.selectbox("Sector (Asistencia)", ["PRODUCCION", "PRESELECCION"], key="p_asist")
        t_asist = c3.selectbox("Turno (Asistencia)", ["1", "2"], key="t_asist")
        
        fecha_s = fecha_dt.strftime('%d-%m-%Y')
        state_key = f"asist_{fecha_s}_{p_asist}_{t_asist}"

        with conectar_db() as conn:
            # Traer asistencia ya guardada
            existente = pd.read_sql("""SELECT operario as Operario, puesto as Tarea, estado as Estado, 
                                    entrada as Entrada, salida as Salida, horas as Horas 
                                    FROM asistencia_diaria WHERE fecha=? AND proceso=? AND turno=?""", 
                                    conn, params=(fecha_s, p_asist, t_asist))
            
            if existente.empty:
                # Si no hay, cargar la nómina maestra de ese sector/turno
                df_m = pd.read_sql("""SELECT nombre || ' ' || apellido as Operario, puesto as Tarea 
                                     FROM personal_maestro WHERE proceso=? AND turno=?""", 
                                   conn, params=(p_asist, t_asist))
                if not df_m.empty:
                    df_final = pd.DataFrame({
                        "Operario": df_m['Operario'], "Tarea": df_m['Tarea'], "Estado": "Presente",
                        "Entrada": "07:00", "Salida": "19:00", "Horas": 12.0
                    })
                else:
                    df_final = pd.DataFrame()
            else:
                df_final = existente

        if not df_final.empty:
            st.info(f"📋 Mostrando nómina de: **{p_asist} - Turno {t_asist}**")
            res_ed = st.data_editor(
                df_final,
                column_config={
                    "Estado": st.column_config.SelectboxColumn("Estado", options=["Presente", "Ausente"]),
                    "Horas": st.column_config.NumberColumn("Hs", format="%.2f", disabled=True)
                },
                use_container_width=True, hide_index=True, key=state_key
            )

            res_ed['Horas'] = res_ed.apply(lambda x: calcular_horas_dinamico(x['Entrada'], x['Salida']) if x['Estado'] == 'Presente' else 0.0, axis=1)

            if st.button("💾 GUARDAR ASISTENCIA", use_container_width=True):
                with conectar_db() as conn:
                    conn.execute("DELETE FROM asistencia_diaria WHERE fecha=? AND proceso=? AND turno=?", (fecha_s, p_asist, t_asist))
                    df_save = res_ed.copy()
                    df_save['fecha'], df_save['proceso'], df_save['turno'] = fecha_s, p_asist, t_asist
                    df_save.rename(columns={'Tarea': 'puesto', 'Operario': 'operario', 'Estado': 'estado', 
                                          'Entrada': 'entrada', 'Salida': 'salida', 'Horas': 'horas'}, inplace=True)
                    df_save.to_sql('asistencia_diaria', conn, if_exists='append', index=False)
                st.success(f"Asistencia guardada."); st.rerun()
        else:
            st.warning(f"No hay personal cargado para {p_asist} T{t_asist}. Cargalo en la pestaña Configuración.")

    with tabs[2]: # CONFIGURACIÓN
        st.subheader("📥 Carga y Edición de Nóminas")
        
        # --- SELECTORES DE CARGA ---
        cc1, cc2 = st.columns(2)
        p_conf = cc1.selectbox("Seleccionar Sector para Cargar", ["PRODUCCION", "PRESELECCION"], key="p_conf")
        t_conf = cc2.selectbox("Seleccionar Turno para Cargar", ["1", "2"], key="t_conf")
        
        st.write(f"Copiá y pegá desde Excel para **{p_conf} - Turno {t_conf}** (Columnas: Puesto | Nombre | Apellido)")
        txt = st.text_area("Pegar datos aquí", height=150, placeholder="Ejemplo: Carretillero	Juan	Perez")
        
        btn_c1, btn_c2 = st.columns(2)
        
        if btn_c1.button(f"🚀 Actualizar Nómina {p_conf} T{t_conf}", use_container_width=True):
            if txt:
                try:
                    df_raw = pd.read_csv(io.StringIO(txt), sep='\t', header=None)
                    df_c = df_raw.iloc[:, [0, 1, 2]].copy()
                    df_c.columns = ['puesto', 'nombre', 'apellido']
                    df_c['proceso'] = p_conf
                    df_c['turno'] = t_conf
                    
                    with conectar_db() as conn:
                        # Borramos SOLO la nómina de ese sector y turno para actualizarla
                        conn.execute("DELETE FROM personal_maestro WHERE proceso=? AND turno=?", (p_conf, t_conf))
                        df_c.to_sql('personal_maestro', conn, if_exists='append', index=False)
                    st.success(f"✅ Nómina de {p_conf} Turno {t_conf} actualizada."); st.rerun()
                except:
                    st.error("Error de formato. Asegurate de copiar 3 columnas (Puesto, Nombre, Apellido).")
        
        if btn_c2.button("🔍 Ver Nómina Actual", use_container_width=True):
            with conectar_db() as conn:
                df_ver = pd.read_sql("SELECT puesto as Puesto, nombre as Nombre, apellido as Apellido FROM personal_maestro WHERE proceso=? AND turno=?", 
                                    conn, params=(p_conf, t_conf))
            if not df_ver.empty:
                st.table(df_ver)
            else:
                st.info("Este sector/turno no tiene personal cargado.")
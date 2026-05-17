import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import base64
import os

# Mantenemos tu ruta de base de datos
DB_PATH = 'greenpack_v4.db'

def f_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def get_base64(bin_file):
    if os.path.exists(bin_file):
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return None

def crear_tabla_usuarios():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                      (usuario TEXT PRIMARY KEY, clave TEXT, rol TEXT)''')

def gestionar_acceso():
    crear_tabla_usuarios()
    
    if 'logueado' not in st.session_state:
        st.session_state.logueado = False

    if not st.session_state.logueado:
        img_fondo = get_base64("static/fondo_login.png")
        img_logo = get_base64("static/logo_login.png")
        
        st.markdown(f'''
            <style>
            /* Fondo de la app general */
            .stApp {{
                background-image: url("data:image/png;base64,{img_fondo}");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}
            header, footer, #MainMenu {{visibility: hidden !important;}}
            .block-container {{padding: 0 !important;}}

            /* CONTENEDOR PADRE: EL VIDRIO RECTANGULAR CENTRADO */
            .login-card {{
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 750px; 
                height: 420px;
                background: rgba(255, 255, 255, 0.08);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border-radius: 30px;
                border: 1px solid rgba(255, 255, 255, 0.15);
                z-index: 10;
            }}

            /* LADO IZQUIERDO: LOGO Y TEXTO (Anclados al vidrio) */
            .left-side {{
                position: absolute;
                top: 50%;
                left: 25%; /* Se ubica en el centro de la mitad izquierda */
                transform: translate(-50%, -50%);
                text-align: center;
                width: 250px;
                z-index: 20;
            }}
            .logo-img {{
                width: 140px !important;
                filter: drop-shadow(0px 4px 8px rgba(0,0,0,0.3));
            }}
            .logo-text {{
                color: white;
                font-size: 34px;
                font-weight: bold;
                margin-top: 5px; /* Justo debajo del logo, sin espacio libre */
                font-family: 'Futura', Arial, sans-serif;
                letter-spacing: 1px;
            }}

            /* LADO DERECHO: TU FORMULARIO (Anclado exactamente a la par del logo) */
            div[data-testid="stForm"] {{
                position: fixed !important;
                top: 88.5% !important; /* Centrado vertical exacto en la pantalla */
                left: calc(50% + 165px) !important; /* Se posiciona simétricamente a la derecha */
                transform: translate(-50%, -50%) !important;
                width: 290px !important;
                background: transparent !important;
                border: none !important;
                z-index: 100 !important;
                padding: 0 !important;
            }}

            /* Inputs estilizados para que encajen estéticamente */
            input {{
                background-color: rgba(255, 255, 255, 0.12) !important;
                color: white !important;
                border: 1px solid rgba(255, 255, 255, 0.25) !important;
                height: 45px !important;
                border-radius: 10px !important;
                font-size: 16px !important;
            }}
            
            input::placeholder {{
                color: rgba(255, 255, 255, 0.6) !important;
            }}

            /* El botón ENTRAR / SOLICITAR REGISTRO */
            .stButton > button {{
                background-color: #00C853 !important;
                color: white !important;
                height: 48px !important;
                font-weight: bold !important;
                font-size: 16px !important;
                border-radius: 12px !important;
                border: none !important;
                width: 100% !important;
                box-shadow: 0 4px 15px rgba(0, 200, 83, 0.4) !important;
                transition: transform 0.1s ease;
            }}
            
            .stButton > button:active {{
                transform: scale(0.98);
            }}

            /* Centrar las opciones de Ingresar/Registrarse */
            .stRadio div[role="radiogroup"] {{
                justify-content: center !important;
                gap: 15px !important;
                margin-bottom: 15px !important;
            }}
            .stRadio label {{ 
                color: white !important; 
                font-weight: bold !important; 
                font-size: 16px !important;
            }}
            </style>
            
            <div class="login-card">
                <div class="left-side">
                    <img src="data:image/png;base64,{img_logo}" class="logo-img">
                    <div class="logo-text">GreenPack</div>
                </div>
            </div>
        ''', unsafe_allow_html=True)

        # Formulario de procesamiento (No romperá el flujo estético gracias al CSS fijo)
        with st.form("login_form"):
            opcion = st.radio("", ["Ingresar", "Registrarse"], horizontal=True, label_visibility="collapsed")
            
            if opcion == "Ingresar":
                u = st.text_input("", placeholder="Usuario", key="u_login", label_visibility="collapsed")
                p = st.text_input("", type="password", placeholder="Contraseña", key="p_login", label_visibility="collapsed")
                
                if st.form_submit_button("ENTRAR"):
                    if u and p:
                        with sqlite3.connect(DB_PATH) as conn:
                            res = conn.execute("SELECT rol FROM usuarios WHERE usuario=? AND clave=?", 
                                             (u, f_hash(p))).fetchone()
                        if res:
                            if res[0] == "pendiente":
                                st.warning("Cuenta pendiente de aprobación")
                            else:
                                st.session_state.logueado = True
                                st.session_state.user_actual = u
                                st.session_state.rol_actual = res[0]
                                st.rerun()
                        else:
                            st.error("Credenciales incorrectas")
                    else:
                        st.warning("Completá los campos")
                        
            else: # Registro
                nu = st.text_input("", placeholder="Nuevo Usuario", key="reg_u", label_visibility="collapsed")
                np = st.text_input("", type="password", placeholder="Nueva Contraseña", key="reg_p", label_visibility="collapsed")
                if st.form_submit_button("SOLICITAR REGISTRO"):
                    if nu and np:
                        try:
                            with sqlite3.connect(DB_PATH) as conn:
                                conn.execute("INSERT INTO usuarios VALUES (?, ?, ?)", (nu, f_hash(np), "pendiente"))
                            st.success("Solicitud enviada")
                        except:
                            st.error("Usuario ya existe")
        st.stop()
def panel_admin():
    st.header("⚙️ Gestión de Permisos")
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query("SELECT usuario, rol FROM usuarios", conn)
    
    st.dataframe(df, use_container_width=True)
    
    with st.form("cambiar_rol"):
        u_sel = st.selectbox("Usuario", df['usuario'].tolist())
        r_sel = st.selectbox("Rol", ["pendiente", "operario1", "operario2", "supervisor", "admin"])
        if st.form_submit_button("Actualizar"):
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("UPDATE usuarios SET rol=? WHERE usuario=?", (r_sel, u_sel))
            st.success(f"Actualizado: {u_sel} ahora es {r_sel}")
            st.rerun()


def panel_admin():
    st.header("👥 Gestión de Usuarios y Permisos")
    
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query("SELECT usuario, rol FROM usuarios", conn)
    
    # Mostramos la tabla para que veas quiénes están
    st.dataframe(df, use_container_width=True)
    
    st.write("---")
    
    # Usamos columnas para separar "Cambiar Rol" de "Borrar"
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Actualizar Rol")
        with st.form("cambiar_rol"):
            u_sel = st.selectbox("Seleccionar Usuario", df['usuario'].tolist(), key="sel_mod")
            r_sel = st.selectbox("Nuevo Rol", ["pendiente", "operario1", "operario2", "supervisor", "admin"])
            if st.form_submit_button("Actualizar Permiso"):
                with sqlite3.connect(DB_PATH) as conn:
                    conn.execute("UPDATE usuarios SET rol=? WHERE usuario=?", (r_sel, u_sel))
                st.success(f"¡{u_sel} ahora es {r_sel}!")
                st.rerun()

    with col2:
        st.subheader("Eliminar Usuario")
        with st.form("borrar_usuario"):
            u_del = st.selectbox("Usuario a eliminar", df['usuario'].tolist(), key="sel_del")
            st.warning(f"¿Estás seguro de borrar a {u_del}?")
            confirmar = st.form_submit_button("❌ ELIMINAR DEFINITIVAMENTE")
            
            if confirmar:
                if u_del == st.session_state.user_actual:
                    st.error("¡No podés borrarte a vos mismo!")
                else:
                    with sqlite3.connect(DB_PATH) as conn:
                        conn.execute("DELETE FROM usuarios WHERE usuario=?", (u_del,))
                    st.success(f"Usuario {u_del} eliminado.")
                    st.rerun()

                    
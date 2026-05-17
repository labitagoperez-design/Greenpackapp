import streamlit as st

st.set_page_config(page_title="Greenpack - Gestión de Citrus", layout="wide", page_icon="🍋")

from streamlit_option_menu import option_menu
import os   
import pandas as pd
import sqlite3
import math
import formulas as fm
import plotly.express as px
import plotly.graph_objects as go
import io 
from datetime import date, datetime, timedelta
import mod_personal as pers_mod
import mod_romaneo as rom_mod
import mod_campo as campo_mod
import mod_importar as imp
import mod_usuarios as mu
import mod_produccion as prod_mod 
from mod_gerencia import mostrar_dashboard_gerencial




# --- CONFIGURACIÓN DE RUTA AL SERVIDOR ---
# Solo cambiamos estas variables para que todo lo demás funcione en red
SERVIDOR_PATH = r"Y:"
DB_PATH = os.path.join(SERVIDOR_PATH, 'greenpack_v4.db') # Mantenemos v4 como tenías
CARPETA_PROCESADOS = os.path.join(SERVIDOR_PATH, 'procesados')



# --- AQUÍ AGREGÁS LA FUNCIÓN MAESTRA ---
def guardar_datos_universal(datos_dict, tabla_nombre):
    db_path = DB_PATH # Usamos la ruta del servidor
    df = pd.DataFrame([datos_dict])
    try:
        conn = sqlite3.connect(db_path)
        try:
            existente = pd.read_sql_query(f"SELECT * FROM {tabla_nombre} LIMIT 1", conn)
            for col in df.columns:
                if col not in existente.columns:
                    conn.execute(f"ALTER TABLE {tabla_nombre} ADD COLUMN '{col}' TEXT")
                    st.toast(f"Actualizando DB: campo '{col}' agregado.")
        except:
            pass
        df.to_sql(tabla_nombre, conn, if_exists='append', index=False)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error al guardar en {tabla_nombre}: {e}")
        return False



# ============================================================
# CSS
# ============================================================
# --- 1. ESTILO CSS ADAPTATIVO PROFESIONAL --- 
st.markdown("""
    <style>
    /* Estilo para los contenedores de métricas y tarjetas */
    [data-testid="stMetric"] {
        background-color: rgba(28, 131, 225, 0.1); /* Azul muy suave transparente */
        border: 1px solid rgba(28, 131, 225, 0.3); /* Borde azul sutil */
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }

    /* Forzar que el texto sea legible en ambos modos */
    [data-testid="stMetricLabel"] {
        color: var(--text-color); /* Color de texto automático del sistema */
        font-weight: bold;
        font-size: 1.1rem !important;
    }

    [data-testid="stMetricValue"] {
        color: #1c83e1; /* Un azul vibrante pero profesional para el dato importante */
        font-weight: 800;
    }

    /* Estilo para las pestañas (Tabs) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: var(--secondary-background-color); /* Gris suave adaptativo */
        border-radius: 5px 5px 0px 0px;
        gap: 1px;
        padding: 10px;
    }

    .stTabs [aria-selected="true"] {
        background-color: #1c83e1 !important; /* Azul Greenpack cuando está seleccionada */
        color: white !important;
    }
    
    /* Mejorar la visualización de las tablas/dataframes */
    .stDataFrame {
        border: 1px solid rgba(28, 131, 225, 0.2);
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)
# --- BUSCÁ ESTA PARTE O AGREGALA CERCA DEL PRINCIPIO ---
def conectar_db():
    return sqlite3.connect(DB_PATH) # Cambiado a ruta servidor


def inicializar_db():
    with conectar_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS registro_paradas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT, turno TEXT, linea TEXT, 
                equipo TEXT, h_inicio TEXT, h_fin TEXT, 
                duracion REAL, detalle TEXT, comentario TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS asistencia_diaria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT, operario TEXT, puesto TEXT, entrada TEXT, 
                salida TEXT, horas REAL, estado TEXT, observacion TEXT
            )
        """)
@st.cache_data(ttl=600)
def cargar_datos_gerenciales():
    def leer_procesado(archivo):
        # CAMBIO: Ahora busca en Y:\procesados
        ruta = os.path.join(CARPETA_PROCESADOS, archivo)
        if os.path.exists(ruta):
            try:
                df = pd.read_csv(ruta, sep=';', encoding='latin-1')
                df.columns = df.columns.str.strip()
                return df
            except: return pd.DataFrame()
        return pd.DataFrame()

    datos = {
        "resumen": leer_procesado('productor por produccion.csv'),
        "cajas": leer_procesado('cajas.csv'),
        "romaneo": leer_procesado('romaneo.csv'),
        "testigos": leer_procesado('testigos.csv')
    }
    
    hoy = datetime.now().strftime('%d-%m-%Y')
    with conectar_db() as conn:
        try:
            datos["paradas"] = pd.read_sql("SELECT * FROM registro_paradas WHERE fecha = ?", conn, params=(hoy,))
        except:
            datos["paradas"] = pd.DataFrame(columns=['duracion', 'fecha'])
        try:
            datos["asistencia"] = pd.read_sql("SELECT * FROM asistencia_diaria WHERE fecha = ?", conn, params=(hoy,))
        except:
            datos["asistencia"] = pd.DataFrame(columns=['horas', 'fecha'])
    return datos
## ============================================================
# BASE DE DATOS — inicialización única y segura
# ============================================================
DB = DB_PATH # Usamos la constante del servidor definida arriba

def init_db():
    conn = conectar_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS preseleccion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT, fecha_cos TEXT, finca TEXT, productor TEXT,
        cantidad INTEGER, color TEXT, visual TEXT, destino TEXT,
        remito TEXT, tiempo_stock TEXT, camara TEXT, fila TEXT,
        volcado TEXT DEFAULT "No", fecha_ingreso TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS bins_terminados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT, fecha TEXT, turno INTEGER, up TEXT, finca TEXT,
        remito TEXT, leves REAL, menor REAL, mayor REAL, calidad TEXT,
        porc_a REAL, porc_b REAL, fecha_cosecha TEXT, observaciones TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS cajas_terminadas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT, n_pallet TEXT, hora TEXT, cliente TEXT,
        destino TEXT, envase TEXT, peso REAL, calidad TEXT, plu TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS stock_playa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT, finca TEXT, destino TEXT, bins INTEGER,
        mercado TEXT, color TEXT, estado TEXT DEFAULT "En Playa"
    )''')

    # Parchear columnas faltantes sin romper datos existentes
    columnas_extra = {
        "preseleccion": [
            ("fecha_ingreso", "TEXT"),
            ("tiempo_stock",  "TEXT"),
            ("codigo",        "TEXT"),
            ("destino",       "TEXT"),
            ("visual",        "TEXT"),
            ("finca",         "TEXT"),
            ("volcado",       "TEXT"),
        ]
    }
    for tabla, cols in columnas_extra.items():
        for col, tipo in cols:
            try:
                c.execute(f"ALTER TABLE {tabla} ADD COLUMN {col} {tipo}")
            except sqlite3.OperationalError:
                pass  # ya existe

    c.execute("UPDATE preseleccion SET volcado='No' WHERE volcado IS NULL")
    conn.commit()
    conn.close()

init_db()

def inicializar_base_de_datos():
    with conectar_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS produccion_embalado (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT, turno INTEGER, finca TEXT,
                kilos REAL, operario TEXT, maquina TEXT
            )
        ''')
        conn.commit()

inicializar_base_de_datos()


# ============================================================
# CONSTANTES
# ============================================================
LISTA_FINCAS = sorted([
    "30 zuccardi","34 zuccardi","Antamapu","Avellaneda","Claudia",
    "Colombres","El 12","El 20","El Arandano","El Azar","El Molino",
    "El Narnajo","El Quincho","El Tajamar","El Tata","El Trece",
    "Elveinte","Famailla Dumit S.A","Greenpack","Greyco","La Argentina",
    "La Escondida","La Luz","Las Mellizas","Las Tipas","Limonares",
    "Los Ceibos","Los Chicos","Los Lapachos","Los Porceles","Los Tarcos",
    "Maria del Rosario","Monte Bello","Monte Grande","Rio Loro",
    "Terra Citrus","Yaquilo"
])
PRODUCTORES = ["Greyco","Agricola Mares","Fruitcrop","Greenpack"]

# ============================================================
# AUTENTICACIÓN
# ============================================================
mu.gestionar_acceso()
rol = st.session_state.rol_actual

# ============================================================
# ALARMA DE LOTES CRÍTICOS (manejo seguro)
# ============================================================

# --- 1. FUNCIÓN PARA LEER LOS ARCHIVOS SIN ERRORES ---
def cargar_dato(nombre):
    ruta = os.path.join(SERVIDOR_PATH, nombre)
    if os.path.exists(ruta):
        try:
            # Leemos el archivo del servidor
            df = pd.read_csv(ruta, sep=None, engine='python', encoding='latin-1')
            
            # 1. Limpiamos nombres de columnas (sacamos espacios extra)
            df.columns = [c.strip() for c in df.columns]
            
            # 2. PARCHE DE SEGURIDAD:
            # Si el código busca 'VISUAL' pero el archivo tiene 'visual', 
            # creamos una copia para que no falle el cruce.
            if 'visual' in df.columns:
                df['VISUAL'] = df['visual']
            elif 'VISUAL' not in df.columns:
                # Si no existe de ninguna forma, la creamos vacía
                df['VISUAL'] = "N/A"
                
            return df
        except Exception as e:
            st.error(f"Error al leer {nombre}: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# --- 2. EL DASHBOARD ---

# ============================================================
# BARRA LATERAL
# ============================================================
with st.sidebar:
    # --- LOGO Y USUARIO ---
    st.write("##")
    try:
        st.image("logo_greenpack.png", use_container_width=True)
    except:
        st.markdown("<h2 style='color:#1c83e1; text-align:center; font-family:sans-serif;'>GREENPACK</h2>", unsafe_allow_html=True)

    st.markdown(f"""
        <div style='text-align:center; color:var(--text-color); opacity: 0.7; margin-bottom:20px;'>
            <small>Usuario Activo:</small><br><b style='color:#1c83e1;'>{st.session_state.user_actual}</b>
        </div>
    """, unsafe_allow_html=True)

    # --- CONFIGURACIÓN DINÁMICA DEL MENÚ ---
    # 1. Definimos las listas básicas
    opciones = ["Inicio", "Preselección", "Producción", "Personal", "Muestras", "Reportes", "Configuracion"]
    iconos = ["house", "lemon", "gear", "people", "clipboard-check", "bar-chart", "sliders"]

    # 2. Agregamos el Panel Gerencial SOLO si es santi_juarez
    
    usuarios_permitidos = ["Santi_Juarez", "admin", "Santiago",]

    if st.session_state.user_actual in usuarios_permitidos:
        opciones.append("Panel Gerencial")
        iconos.append("graph-up") # Importante: mismo número de iconos que de opciones

    # 3. CREACIÓN DEL MENÚ
    area = option_menu(
        None, 
        opciones, 
        icons=iconos, 
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#1c83e1", "font-size": "18px"},
            "nav-link": {
                "color": "var(--text-color)", 
                "font-size": "14px", 
                "text-align": "left", 
                "margin": "5px", 
                "font-family": "sans-serif",
                "--hover-color": "rgba(28, 131, 225, 0.1)"
            },
            "nav-link-selected": {
                "background-color": "#1c83e1", 
                "color": "white", 
                "font-weight": "600"
            },
        }
    )

    st.write("##")

    # --- BOTÓN Y PIE DE PÁGINA ---
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.logueado = False
        st.rerun()

    st.markdown("""
        <div style='border-top: 1px solid rgba(28, 131, 225, 0.2); padding-top: 20px; text-align:center; font-family:sans-serif;'>
            <b style='color:var(--text-color); font-size: 0.6rem;'>SANTIAGO PEREZ</b><br>
            <span style='color:#1c83e1; font-size: 0.5rem; font-weight: bold;'>Software & Mantenimiento</span><br>
            <span style='color:var(--text-color); opacity: 0.5; font-size: 0.6rem;'>v4.0 | 2026</span>
        </div>
    """, unsafe_allow_html=True)

# ============================================================
# INICIO
# ============================================================
if area == "Inicio":
    st.title(f"👋 ¡Hola, {st.session_state.get('user_actual','Usuario')}!")
    st.write(f"Bienvenido al **Sistema de Gestión Greenpack**. Rol: `{st.session_state.get('rol_actual','Sin Rol')}`")
    st.markdown("---")

    
    try:
        # Forzamos la actualización de datos para que coincida con la nueva carga
        st.cache_data.clear()

        with conectar_db() as conn_inicio:
            # Traemos la fruta que está en stock (volcado = 0)
            df_fuente = pd.read_sql_query("SELECT * FROM tabla_maestra_final WHERE volcado = 0 OR volcado = '0'", conn_inicio)

        if not df_fuente.empty:
            # 1. NORMALIZACIÓN TOTAL
            df_fuente.columns = [str(c).strip().lower() for c in df_fuente.columns]
            
            # Limpieza de códigos y duplicados (mismo motor que el Dashboard)
            df_fuente['codigo'] = df_fuente['codigo'].astype(str).str.strip().str.upper()
            df_fuente = df_fuente.drop_duplicates(subset=['codigo'], keep='last').copy()

            # Aseguramos que 'destino' sea texto limpio y 'cantidad' sea número
            df_fuente['destino'] = df_fuente['destino'].astype(str).str.strip().str.upper()
            df_fuente['cantidad'] = pd.to_numeric(df_fuente['cantidad'], errors='coerce').fillna(0)
            
            # --- 2. FILTRO DE MADURACIÓN (A + P) ---
            col_v = 'visual' if 'visual' in df_fuente.columns else 'visual_proyectada'
            
            # Filtramos el DataFrame para que SOLO contenga lo listo para procesar
            mask_listos = df_fuente[col_v].astype(str).str.strip().str.upper().isin(['P', 'A'])
            df_listos = df_fuente[mask_listos].copy()

            if not df_listos.empty:
                st.markdown("<h3 style='color: #1E3A8A;'>🍋 Bines listos para procesar hoy (A + P)</h3>", unsafe_allow_html=True)

                # --- 3. LÓGICA DE MÉTRICAS ACTUALIZADA ---
                def get_datos_final(destino_id, df):
                    # Filtro inteligente para destinos
                    if destino_id == "NO UE":
                        df_m = df[df['destino'].str.contains('NO', na=False)]
                    elif destino_id == "UE":
                        # Que contenga UE pero que NO contenga NO
                        df_m = df[(df['destino'].str.contains('UE', na=False)) & (~df['destino'].str.contains('NO', na=False))]
                    else:
                        # Para USA u otros
                        df_m = df[df['destino'].str.contains(destino_id, na=False)]
                    
                    # SUMA de la columna cantidad
                    bins = int(df_m['cantidad'].sum())
                    
                    kilos = bins * 370
                    p_altos = kilos / (72 * 18) if kilos > 0 else 0
                    p_bajos = kilos / (63 * 18) if kilos > 0 else 0
                    
                    return bins, kilos, round(p_altos, 1), round(p_bajos, 1)

                # Obtención de datos con la nueva función
                b_ue, k_ue, pa_ue, pb_ue = get_datos_final("UE", df_listos)
                b_usa, k_usa, pa_usa, pb_usa = get_datos_final("USA", df_listos)
                b_noue, k_noue, pa_noue, pb_noue = get_datos_final("NO UE", df_listos)

                # Métrica General
                total_bins_listos = b_ue + b_usa + b_noue
                st.metric("TOTAL BINES LISTOS (Hoy)", f"{total_bins_listos} Bins")

                # RENDERIZADO DE TARJETAS
                m1, m2, m3 = st.columns(3)
                config = [
                    (m1, "🇪🇺 EUROPA", b_ue, k_ue, pa_ue, pb_ue),
                    (m2, "🇺🇸 EE.UU.", b_usa, k_usa, pa_usa, pb_usa),
                    (m3, "🌐 OTROS / NO UE", b_noue, k_noue, pa_noue, pb_noue)
                ]

                for col, titulo, b, k, pa, pb in config:
                    with col:
                        st.markdown(f"""
                            <div style='background-color: #1E3A8A; padding: 15px; border-radius: 10px; color: white; min-height: 210px;'>
                                <p style='margin:0; font-size: 13px; font-weight: bold; color: #a5b4fc;'>{titulo}</p>
                                <h1 style='margin:0; color: white; font-size: 38px;'>{b} Bins</h1>
                                <p style='margin:0; color: #2ecc71; font-weight: bold; font-size: 17px;'>{k:,} kg aprox.</p>
                                <hr style='margin:8px 0; opacity: 0.2;'>
                                <p style='margin:0; font-size: 12px;'>
                                    Pallets Altos (x72): <b>{pa}</b><br>
                                    Pallets Bajos (x63): <b>{pb}</b>
                                </p>
                            </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No hay bines en estado A o P para procesar hoy.")
        else:
            st.warning("No hay bines en stock (volcado=0).")

    except Exception as e:
        st.error(f"Error en tarjetas de inicio: {e}")

    # Simulador de proyección
    with st.expander("🔮 Simulador de Proyección Estratégica", expanded=True):
        st.markdown("### Configuración de Cosecha")
    
    # Asegúrate de que LISTA_FINCAS esté definida en tu código global
    if 'LISTA_FINCAS' not in locals():
        LISTA_FINCAS = ["Finca Claudia", "Finca El Molino", "Yaquilo", "Antamapu", "La Luz"]

    # Inicialización del session_state
    if "frentes_cosecha" not in st.session_state:
        st.session_state.frentes_cosecha = [{
            "finca": LISTA_FINCAS[0], "bins": 100, "rendimiento": 80, "dias": 1,
            "p_vo": 10, "p_v": 15, "p_vc": 20, "p_p": 25, "p_a": 30
        }]

    if st.button("➕ Agregar Finca / Frente de Cosecha"):
        st.session_state.frentes_cosecha.append({
            "finca": LISTA_FINCAS[0], "bins": 100, "rendimiento": 80, "dias": 1,
            "p_vo": 10, "p_v": 15, "p_vc": 20, "p_p": 25, "p_a": 30
        })
        st.rerun()

    frentes_para_borrar = []
    
    # Variables para acumular el resultado final de TODOS los frentes
    bins_listos_totales = 0
    rend_acumulado = 0

    for i, frente in enumerate(st.session_state.frentes_cosecha):
        with st.container(border=True):
            col_titulo, col_borrar = st.columns([5, 1])
            col_titulo.markdown(f"**Frente {i+1}**")
            if col_borrar.button("🗑️", key=f"del_{i}") and len(st.session_state.frentes_cosecha) > 1:
                frentes_para_borrar.append(i)
            
            col_c1, col_c2, col_c3 = st.columns(3)
            frente["finca"] = col_c1.selectbox("Finca", LISTA_FINCAS,
                index=LISTA_FINCAS.index(frente["finca"]) if frente["finca"] in LISTA_FINCAS else 0,
                key=f"finca_{i}")
            frente["bins"] = col_c2.number_input("Bins por día", value=frente.get("bins", 100), min_value=1, key=f"nbins_{i}")
            frente["rendimiento"] = col_c3.slider("Rendimiento %", 0, 100, frente.get("rendimiento", 80), key=f"rend_{i}")
            
            # SLIDER INDIVIDUAL (Limitado de 0 a 7 días como pediste)
            frente["dias"] = st.select_slider(
                f"Días a proyectar para {frente['finca']}", 
                options=[0, 1, 2, 3, 4, 5, 6, 7], 
                value=frente.get("dias", 1), 
                key=f"slider_dias_{i}"
            )

            # DISTRIBUCIÓN POR COLOR INDIVIDUAL
            st.write(f"**Distribución de Color (%)**")
            cc1, cc2, cc3, cc4, cc5 = st.columns(5)
            frente["p_vo"] = cc1.number_input("VO (7d) %", value=frente.get("p_vo", 10), key=f"s_vo_{i}")
            frente["p_v"]  = cc2.number_input("V (6d) %",  value=frente.get("p_v", 15),  key=f"s_v_{i}")
            frente["p_vc"] = cc3.number_input("VC (5d) %", value=frente.get("p_vc", 20), key=f"s_vc_{i}")
            frente["p_p"]  = cc4.number_input("P (3d) %",  value=frente.get("p_p", 25),  key=f"s_p_{i}")
            frente["p_a"]  = cc5.number_input("A (Listo) %", value=frente.get("p_a", 30), key=f"s_a_{i}")

            check_suma = frente["p_vo"] + frente["p_v"] + frente["p_vc"] + frente["p_p"] + frente["p_a"]
            
            if check_suma == 100:
                # 1. Calculamos los Bins Netos Totales de este frente (sin importar el color todavía)
                # Fórmula: Bins/Día * Rendimiento * Coeficiente 1.085
                # Nota: Aquí no multiplicamos por días todavía porque los días determinan qué COLOR entra
                bn_diario = (frente["bins"] * (frente["rendimiento"] / 100) * 1.085)
                
                # 2. Aplicamos tu LÓGICA DE DÍAS a este frente específico
                # b_a (Amarillo) siempre entra. Los demás dependen del slider de este frente.
                b_a  = bn_diario * (frente["p_a"] / 100)
                b_p  = bn_diario * (frente["p_p"] / 100)
                b_vc = bn_diario * (frente["p_vc"] / 100)
                b_v  = bn_diario * (frente["p_v"] / 100)
                b_vo = bn_diario * (frente["p_vo"] / 100)
                
                frente_listos = b_a
                if frente["dias"] >= 3: frente_listos += b_p
                if frente["dias"] >= 5: frente_listos += b_vc
                if frente["dias"] >= 6: frente_listos += b_v
                if frente["dias"] >= 7: frente_listos += b_vo
                
                # Sumamos al acumulador total (esto suma todos los frentes)
                bins_listos_totales += frente_listos
                rend_acumulado += frente["rendimiento"]
                
                st.caption(f"✅ {frente['finca']}: {math.ceil(frente_listos)} bins listos para procesar al día {frente['dias']}")
            else:
                st.error(f"⚠️ Suma: {check_suma}% (Debe ser 100%)")

    # Lógica de borrado
    if frentes_para_borrar:
        for idx in sorted(frentes_para_borrar, reverse=True):
            st.session_state.frentes_cosecha.pop(idx)
        st.rerun()

    st.divider()

    # --- RESULTADOS FINALES ---
    if bins_listos_totales > 0:
        bins_finales = math.ceil(bins_listos_totales)
        kilos_finales = bins_finales * 370
        rend_promedio = rend_acumulado / len(st.session_state.frentes_cosecha)

        # Tus fórmulas eval()
        fa, fb, fc = st.columns(3)
        f_bins    = fa.text_input("Fórmula Bins", value="bins", key="f_bins")
        f_kilos   = fb.text_input("Fórmula Kilos", value="bins * 370", key="f_kilos")
        f_pallets = fc.text_input("Fórmula Pallets", value="bins * 0.37 * 0.85", key="f_pallets")

        vars_f = {"bins": bins_finales, "rendimiento": rend_promedio, "kilos": kilos_finales, 
                  "math": math, "ceil": math.ceil, "round": round}

        def evaluar(formula, vv):
            try: return round(eval(formula, {"__builtins__": {}}, vv), 2), None
            except Exception as e: return None, str(e)

        res_b, err_b = evaluar(f_bins, vars_f)
        res_k, err_k = evaluar(f_kilos, vars_f)
        res_p, err_p = evaluar(f_pallets, vars_f)

        st.subheader("📊 Resultado Consolidado (Suma de todos los frentes)")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Bins Totales", f"{math.ceil(res_b)}" if not err_b else "❌")
        m2.metric("Kilos Est.", f"{int(res_k):,} kg" if not err_k else "❌")
        if not err_p:
            m3.metric("Pallet Alto", f"{round(res_p/1.3, 1)}")
            m4.metric("Pallet Bajo", f"{round(res_p/1.2, 1)}")

    # Filtros y exportación
    with st.expander("🔍 Filtros de Detalle y Exportación", expanded=False):
        with conectar_db() as conn_exp:
            df_f = pd.read_sql_query(
                "SELECT DISTINCT productor, destino FROM preseleccion WHERE volcado='No'", conn_exp)
            df_f.columns = [str(c).strip().lower() for c in df_f.columns]
            prod_unicos = sorted([str(x) for x in df_f['productor'].dropna().unique()])
            dest_unicos = sorted([str(x) for x in df_f['destino'].dropna().unique()])

            f1, f2 = st.columns(2)
            sel_p = f1.selectbox("Productor:", ["Todos"] + prod_unicos, key="exp_prod")
            sel_d = f2.selectbox("Destino:",   ["Todos"] + dest_unicos, key="exp_dest")

            q = "SELECT * FROM preseleccion WHERE volcado='No'"
            if sel_p != "Todos": q += f" AND productor='{sel_p}'"
            if sel_d != "Todos": q += f" AND destino='{sel_d}'"
            df_exp = pd.read_sql_query(q, conn_exp)
            st.dataframe(df_exp, use_container_width=True)
            csv = df_exp.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar CSV", data=csv, file_name="Reporte.csv", mime="text/csv")


# ============================================================
# PRESELECCIÓN (VERSION CALIBRADA CON FILTROS DINÁMICOS CRUZADOS)
# ============================================================
elif area == "Preselección":
    with st.sidebar:
        selected = option_menu(
            "Preselección",
            ["1. Ingreso de fruta", "2. Stock color", "3. Dashboard", "4. Stock Playa"],
            icons=["box-arrow-in-right", "check2-square", "speedometer2", "truck"],
            menu_icon="cast", default_index=0
        )

    # Aseguramos el índice único antibloqueo en la base de datos
    with conectar_db() as conn:
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_codigo_unico ON tabla_maestra_final(codigo);")
        conn.commit()

    # ----------------------------------------------------------
    # 1. INGRESO DE FRUTA (CONEXIÓN EN VIVO A EXCEL + EDICIÓN)
    # ----------------------------------------------------------
    if selected == "1. Ingreso de fruta":
        st.header("📝 Libro de Ingreso de Fruta (Lectura en Vivo)")

        # RUTAS DEL ARCHIVO PARTE DIARIO
        ruta_red_parte = r"Y:\Despacho\APP_GREENPACK\datos_origen\Parte diario 2025.xlsx"
        ruta_local_parte = os.path.join(os.getcwd(), "parte_diario_local.xlsx")
        ruta_desencriptado_parte = os.path.join(os.getcwd(), "parte_diario_libre.xlsx")

        df_excel = None

        # --- 1. ESCUDO DE RED: COPIA EN CALIENTE ---
        try:
            if os.path.exists(ruta_red_parte):
                import shutil
                shutil.copy2(ruta_red_parte, ruta_local_parte)
        except Exception:
            pass

        # --- 2. DESENCRIPTACIÓN AUTOMÁTICA (ROCKO1) ---
        archivo_a_descifrar = ruta_local_parte if os.path.exists(ruta_local_parte) else ruta_red_parte

        if os.path.exists(archivo_a_descifrar):
            with st.spinner("🔄 Sincronizando datos en vivo desde el Parte Diario de red..."):
                try:
                    import msoffcrypto
                    with open(archivo_a_descifrar, "rb") as f_encrypted:
                        office_file = msoffcrypto.OfficeFile(f_encrypted)
                        office_file.load_key(password="ROCKO1")
                        with open(ruta_desencriptado_parte, "wb") as f_decrypted:
                            office_file.decrypt(f_decrypted)

                    # --- 3. LECTURA DE LA HOJA 'PARTE' ---
                    if os.path.exists(ruta_desencriptado_parte):
                        df_excel = pd.read_excel(ruta_desencriptado_parte, sheet_name="PARTE", engine="openpyxl")
                        try:
                            os.remove(ruta_desencriptado_parte)
                        except Exception:
                            pass
                except Exception as e:
                    st.error(f"❌ Error al desencriptar o leer el Excel: {e}")
        else:
            st.warning(f"⚠️ No se detectó el archivo en red: {ruta_red_parte}")

        # --- 4. ALIMENTACIÓN / ACTUALIZACIÓN DE SQLITE ---
        if df_excel is not None:
            try:
                # Limpiamos nombres de columnas del Excel de Oscar
                df_excel.columns = [str(c).strip().upper() for c in df_excel.columns]
                df_excel = df_excel[df_excel['CODIGO'].notna()]

                with conectar_db() as conn:
                    cursor = conn.cursor()
                    
                    for _, row in df_excel.iterrows():
                        codigo_clean = str(row.get('CODIGO', '')).strip().upper()
                        if codigo_clean in ['', 'NAN', 'NONE']:
                            continue

                        # Procesamiento inteligente de fechas
                        def formatear_fecha(val):
                            v = str(val).strip().lower()
                            if v in ["", "nan", "none", "0"]: return None
                            try:
                                meses = {'jan':'01','feb':'02','mar':'03','apr':'04','may':'05','jun':'06',
                                         'jul':'07','aug':'08','sep':'09','oct':'10','nov':'11','dec':'12',
                                         'ene':'01','abr':'04','ago':'08','dic':'12'}
                                for esp, num in meses.items():
                                    if esp in v:
                                        dia = v.split('-')[0].strip().zfill(2)
                                        return f"2026-{num}-{dia}"
                                return pd.to_datetime(v, dayfirst=True).strftime('%Y-%m-%d')
                            except:
                                return v

                        f_parte = formatear_fecha(row.get('FECHA DE PARTE', ''))
                        f_cosecha = formatear_fecha(row.get('FECHA DE COSECHA', ''))

                        # Mapeo de Volcado y Cantidad numérica
                        v_prod_raw = str(row.get('VOLCADO A PROD.', '0')).replace(',', '.')
                        try: volcado_final = 1 if float(v_prod_raw) >= 1 else 0
                        except: volcado_final = 0

                        cant_val = str(row.get('CANTIDAD', '0')).replace(',', '.')
                        try: cantidad_final = float(cant_val)
                        except: cantidad_final = 0

                        # Sincronización Espejo: Insertamos si no existe. 
                        # Si ya existe, actualizamos todo MENOS el 'visual' y 'calidad' para no pisar tu trabajo manual.
                        cursor.execute("""
                            INSERT INTO tabla_maestra_final (
                                codigo, fecha_de_parte, fecha_de_cosecha, camara, fila, 
                                destino, up, color, cantidad, finca, productor, volcado, visual, calidad
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(codigo) DO UPDATE SET
                                fecha_de_parte = excluded.fecha_de_parte,
                                fecha_de_cosecha = excluded.fecha_de_cosecha,
                                camara = excluded.camara,
                                fila = excluded.fila,
                                destino = excluded.destino,
                                up = excluded.up,
                                color = excluded.color,
                                cantidad = excluded.cantidad,
                                finca = excluded.finca,
                                productor = excluded.productor,
                                volcado = excluded.volcado
                        """, (
                            codigo_clean, f_parte, f_cosecha,
                            str(row.get('CAMARA', '')).strip(),
                            str(row.get('FILA', '')).strip(),
                            str(row.get('DESTINO', '')).strip(),
                            str(row.get('UP', '')).strip(),
                            str(row.get('COLOR', '')).strip(),
                            cantidad_final,
                            str(row.get('FINCA', '')).strip(),
                            str(row.get('PRODUTOR', 'A MARES')).strip().upper(),
                            volcado_final,
                            str(row.get('A', 'N/A')).strip().upper(), # Por defecto usa el del excel si es nuevo
                            str(row.get('CALIDAD', 'N/A')).strip().upper()
                        ))
                    conn.commit()
            except Exception as e:
                st.error(f"❌ Error al procesar matriz de datos en vivo: {e}")

        # --- 5. LECTURA FINAL PARA MOSTRAR EN PANTALLA ---
        df_view = pd.DataFrame()
        try:
            with conectar_db() as conn:
                df_view = pd.read_sql_query("SELECT * FROM tabla_maestra_final", conn)
        except Exception:
            pass

        if not df_view.empty:
            # Normalización para filtros cruzados de la App
            df_view['productor'] = df_view['productor'].astype(str).str.strip().str.upper()
            df_view['finca'] = df_view['finca'].astype(str).str.strip().str.upper()
            df_view['color'] = df_view['color'].astype(str).str.strip().str.upper()

            # PANEL DE FILTROS AVANZADOS MULTISELECCIÓN
            with st.expander("🔍 PANEL DE FILTROS AVANZADOS (Multiselección)", expanded=True):
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    list_prod = sorted([x for x in df_view['productor'].unique() if x not in ['NAN', '']])
                    prod_sel = st.multiselect("Filtrar Productor:", list_prod, placeholder="Todos")
                with c2:
                    df_temp_f = df_view[df_view['productor'].isin(prod_sel)] if prod_sel else df_view
                    list_finca = sorted([x for x in df_temp_f['finca'].unique() if x not in ['NAN', '']])
                    finca_sel = st.multiselect("Filtrar Finca:", list_finca, placeholder="Todas")
                with c3:
                    df_temp_c = df_temp_f[df_temp_f['finca'].isin(finca_sel)] if finca_sel else df_temp_f
                    list_col = sorted([x for x in df_temp_c['color'].unique() if x not in ['NAN', '']])
                    col_sel = st.multiselect("Filtrar Color:", list_col, placeholder="Todos")
                with c4:
                    f_volcado = st.selectbox("Estado Volcado:", ["TODOS", "PENDIENTE (0)", "VOLCADO (1)"])

            # Aplicamos filtros
            dff = df_view.copy()
            if prod_sel: dff = dff[dff['productor'].isin(prod_sel)]
            if finca_sel: dff = dff[dff['finca'].isin(finca_sel)]
            if col_sel: dff = dff[dff['color'].isin(col_sel)]
            
            if f_volcado == "PENDIENTE (0)": dff = dff[dff['volcado'] == 0]
            elif f_volcado == "VOLCADO (1)": dff = dff[dff['volcado'] == 1]

            orden = [
                'codigo', 'fecha_de_parte', 'camara', 'fila', 'visual', 'calidad',
                'destino', 'color', 'cantidad', 'finca', 'productor', 'volcado'
            ]
            cols_finales = [c for c in orden if c in dff.columns]

            st.markdown("### 📊 Tablero de Control de Bines (Podés modificar 'Visual' y 'Calidad')")

            # EDITOR INTERACTIVO CON COMBOS DESPLEGABLES
            df_editado = st.data_editor(
                dff[cols_finales],
                use_container_width=True,
                hide_index=True,
                key="editor_vivo_preseleccion",
                column_config={
                    "visual": st.column_config.SelectboxColumn("Visual (Maduración)", options=["VO", "V", "VC", "P", "A"], required=True),
                    "calidad": st.column_config.SelectboxColumn("Calidad", options=["EXPORTACION", "MERCADO", "DESCARTE", "N/A"]),
                    "volcado": st.column_config.CheckboxColumn("Volcado ✔️"),
                    "cantidad": st.column_config.NumberColumn("Bins", disabled=True)
                }
            )

            # BOTÓN DE GUARDADO SEGURO
            if st.button("💾 Guardar Modificaciones Manuales", use_container_width=True):
                try:
                    with conectar_db() as conn:
                        cursor = conn.cursor()
                        for _, fila in df_editado.iterrows():
                            cursor.execute("""
                                UPDATE tabla_maestra_final 
                                SET visual = ?, calidad = ?, volcado = ? 
                                WHERE codigo = ?
                            """, (
                                str(fila['visual']).strip().upper(),
                                str(fila['calidad']).strip().upper(),
                                1 if fila['volcado'] else 0,
                                str(fila['codigo']).strip().upper()
                            ))
                        conn.commit()
                    st.success("✅ ¡Cambios guardados con éxito! Datos sincronizados.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al guardar modificaciones: {e}")

            st.caption(f"Mostrando {len(dff)} bines activos.")

    # ----------------------------------------------------------
    # 2. STOCK EN CÁMARAS (PISO) - CONTROL DE ALERTAS CRÍTICAS
    # ----------------------------------------------------------
    elif selected == "2. Stock color":
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=60000, key="refresh_piso_minuto")

        st.header("📦 Stock en Cámaras (Piso)")

        if st.button("🔄 Sincronizar y Limpiar Duplicados", use_container_width=True):
            try:
                with conectar_db() as conn:
                    conn.execute("""
                        DELETE FROM tabla_maestra_final 
                        WHERE rowid NOT IN (
                            SELECT MIN(rowid) FROM tabla_maestra_final GROUP BY codigo
                        )
                    """)
                    conn.commit()
                st.cache_data.clear() 
                st.success("✅ Datos sincronizados correctamente.")
                st.rerun() 
            except Exception as e:
                st.error(f"Error: {e}")

        try:
            with conectar_db() as conn:
                df_piso = pd.read_sql_query("SELECT * FROM tabla_maestra_final", conn)

            if not df_piso.empty:
                df_piso.columns = [c.upper().strip() for c in df_piso.columns]
                
                df_piso['VOLCADO'] = pd.to_numeric(df_piso['VOLCADO'], errors='coerce').fillna(0).astype(int)
                df_piso['CANTIDAD'] = pd.to_numeric(df_piso['CANTIDAD'], errors='coerce').fillna(0)
                
                # Excluimos la fruta que ya fue volcada a producción
                df_piso = df_piso[df_piso['VOLCADO'] != 1].copy()

                # Antigüedad en piso (Alarma de 10 días)
                df_piso['FECHA_DT'] = pd.to_datetime(df_piso['FECHA_DE_PARTE'], errors='coerce')
                hoy = pd.Timestamp(datetime.now().date())
                df_piso['DIAS_PISO'] = (hoy - df_piso['FECHA_DT']).dt.days.fillna(0).astype(int)

                df_unicos = df_piso.copy()
                df_unicos['VISUAL_CLEAN'] = df_unicos['VISUAL'].astype(str).str.strip().str.upper()
                
                mask_camara = df_unicos['VISUAL_CLEAN'].isin(['VO', 'V', 'VC'])
                
                stock_total_real = int(df_unicos['CANTIDAD'].sum())
                stock_solo_camara = int(df_unicos[mask_camara]['CANTIDAD'].sum())
                
                CAPACIDAD_MAX = 2740

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Stock Total Real", f"{stock_total_real} Bins")
                m2.metric("Total en Cámara", f"{stock_solo_camara} Bins")
                m3.metric("Espacio Libre", f"{CAPACIDAD_MAX - stock_solo_camara} Bins")
                m4.metric("Ocupación", f"{(stock_solo_camara/CAPACIDAD_MAX):.1%}")

                # Alerta visual persistente por bines estancados
                bines_viejos = df_unicos[(df_unicos['DIAS_PISO'] >= 10) & (mask_camara)]
                if not bines_viejos.empty:
                    st.error(f"⚠️ ATENCIÓN DE CONTROL DE CALIDAD: Hay {len(bines_viejos)} bines que superan los 10 días de permanencia en piso.")

                st.divider()
                st.subheader("📝 Listado de Bines Activos en Planta")
                
                dff = df_unicos[['CODIGO', 'COLOR', 'DESTINO', 'PRODUCTOR', 'CANTIDAD', 'VISUAL', 'DIAS_PISO']].copy()
                
                st.data_editor(
                    dff, use_container_width=True, hide_index=True,
                    column_config={
                        "DIAS_PISO": st.column_config.NumberColumn("DÍAS EN PISO ⏰", format="%d días"),
                        "CANTIDAD": st.column_config.NumberColumn("CANT.", format="%d")
                    }
                )

        except Exception as e:
            st.error(f"❌ Error en el módulo de Stock: {e}")

    # ----------------------------------------------------------
    # 3. DASHBOARD INTERACTIVO (CON FILTROS ANALÍTICOS)
    # ----------------------------------------------------------
    elif selected == "3. Dashboard":
        from streamlit_autorefresh import st_autorefresh
        import plotly.express as px
        
        st_autorefresh(interval=3600000, key="datarefresh") 
        st.cache_data.clear()
        
        st.info("⏳ Los datos de este tablero se actualizan al cierre de cada turno.")
        st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>📊 Panel de Control Operativo</h1>", unsafe_allow_html=True)

        try:
            with conectar_db() as conn_d:
                df_dash = pd.read_sql_query("SELECT * FROM tabla_maestra_final", conn_d)
        except Exception as e:
            st.error(f"Error al leer la base de datos: {e}")
            df_dash = pd.DataFrame()

        if not df_dash.empty:
            df_dash.columns = [str(c).strip().lower() for c in df_dash.columns]
            df_dash['codigo'] = df_dash['codigo'].astype(str).str.strip().str.upper()
            df_dash = df_dash[~df_dash['codigo'].isin(['NAN', '', 'NONE', '0'])]
            df_dash = df_dash.drop_duplicates(subset=['codigo'], keep='last').copy()
            df_dash['volcado'] = pd.to_numeric(df_dash['volcado'], errors='coerce').fillna(0).astype(int)
            df_dash = df_dash[df_dash['volcado'] == 0].copy()
            df_dash['cantidad'] = pd.to_numeric(df_dash['cantidad'], errors='coerce').fillna(0).astype(int)

            st.markdown("### 📊 Resumen General de Planta")
            
            total_bines_camara = int(df_dash['cantidad'].sum())
            col_target = 'visual' if 'visual' in df_dash.columns else 'color'
            bines_amarillos_total = int(df_dash[df_dash[col_target].astype(str).str.strip().str.upper() == 'A']['cantidad'].sum())
            kilos_planta = total_bines_camara * 370

            tg1, tg2, tg3 = st.columns(3)
            
            with tg1:
                st.markdown(f"""
                    <div style='background-color: #0e1117; padding: 20px; border-radius: 10px; border: 1px solid #3B82F6; text-align: center;'>
                        <p style='color: #94A3B8; font-size: 14px; margin: 0;'>TOTAL EN CÁMARA</p>
                        <h1 style='color: white; margin: 0; font-size: 48px;'>{total_bines_camara}</h1>
                        <p style='color: #3B82F6; font-size: 12px; margin: 0;'>Bines en Stock Real</p>
                    </div>
                """, unsafe_allow_html=True)

            with tg2:
                st.markdown(f"""
                    <div style='background-color: #0e1117; padding: 20px; border-radius: 10px; border: 1px solid #EAB308; text-align: center;'>
                        <p style='color: #94A3B8; font-size: 14px; margin: 0;'>LISTOS (AMARILLOS)</p>
                        <h1 style='color: #EAB308; margin: 0; font-size: 48px;'>{bines_amarillos_total}</h1>
                        <p style='color: #EAB308; font-size: 12px; margin: 0;'>Total para Producir Hoy</p>
                    </div>
                """, unsafe_allow_html=True)

            with tg3:
                st.markdown(f"""
                    <div style='background-color: #0e1117; padding: 20px; border-radius: 10px; border: 1px solid #22C55E; text-align: center;'>
                        <p style='color: #94A3B8; font-size: 14px; margin: 0;'>KILOS ESTIMADOS</p>
                        <h1 style='color: #22C55E; margin: 0; font-size: 48px;'>{kilos_planta:,}</h1>
                        <p style='color: #22C55E; font-size: 12px; margin: 0;'>Kilos totales en piso</p>
                    </div>
                """, unsafe_allow_html=True)
            
            st.divider()

            def asignar_mercado(destino_str):
                d = str(destino_str).upper()
                if 'NO' in d: return 'NOUE'
                if 'USA' in d or 'EE' in d: return 'USA'
                if 'UE' in d or 'EUROPA' in d: return 'UE'
                return 'OTROS'

            df_dash['mercado_limpio'] = df_dash['destino'].apply(asignar_mercado)

            # --- PROYECCIÓN INTERACTIVA DE MADURACIÓN ---
            tiempos = {'VO': 7, 'V': 5, 'VC': 3, 'P': 2, 'A': 0}
            dias_sim = st.select_slider("📅 Proyectar maduración (Días simulados):", options=[0, 1, 2, 3, 5, 7], value=0)

            def calcular_proyeccion(v_orig, dias_t):
                v_orig = str(v_orig).upper().strip()
                if v_orig not in tiempos: return v_orig
                return 'A' if dias_t >= tiempos.get(v_orig, 5) else v_orig

            col_v = 'visual' if 'visual' in df_dash.columns else 'color'
            df_dash['visual_proyectada'] = df_dash[col_v].apply(lambda x: calcular_proyeccion(x, dias_sim))

            st.divider()
            mercados_config = [
                ("USA", "🇺🇸 EE.UU."), 
                ("UE", "🇪🇺 EUROPA"), 
                ("NOUE", "🌐 OTROS (NO UE)")
            ]
            cols_m = st.columns(3)

            for i, (m_id, m_titulo) in enumerate(mercados_config):
                df_m = df_dash[df_dash['mercado_limpio'] == m_id].copy()
                bins_totales = int(df_m['cantidad'].sum()) 
                bines_listos = int(df_m[df_m['visual_proyectada'] == 'A']['cantidad'].sum())
                kilos_listos = bines_listos * 370
                
                p_altos = kilos_listos / (72 * 18) if kilos_listos > 0 else 0
                p_bajos = kilos_listos / (63 * 18) if kilos_listos > 0 else 0
                
                with cols_m[i]:
                    st.markdown(f"""
                        <div style='background-color: #1E3A8A; padding: 15px; border-radius: 10px; color: white; min-height: 230px;'>
                            <p style='margin:0; font-size: 13px; font-weight: bold; color: #a5b4fc;'>{m_titulo}</p>
                            <h1 style='margin:0; color: white; font-size: 42px;'>{bins_totales} Bins</h1>
                            <p style='margin:5px 0; color: #2ecc71; font-weight: bold; font-size: 18px;'>{bines_listos} Listos ({kilos_listos:,} kg)</p>
                            <hr style='margin:8px 0; opacity: 0.2;'>
                            <p style='margin:0; font-size: 11px;'>Pallets Altos (x72): <b>{p_altos:.1f}</b></p>
                            <p style='margin:0; font-size: 11px;'>Pallets Bajos (x63): <b>{p_bajos:.1f}</b></p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    resumen_v = df_m.groupby('visual_proyectada')['cantidad'].sum().reindex(["VO","V","VC","P","A"]).fillna(0).astype(int)
                    st.dataframe(resumen_v, use_container_width=True)

            st.divider()
            c_g1, c_g2 = st.columns(2)
            with c_g1:
                fig_pie = px.pie(df_dash, names='visual_proyectada', values='cantidad', title="Distribución de Stock por Maduración")
                st.plotly_chart(fig_pie, use_container_width=True)
            with c_g2:
                df_prod = df_dash.groupby('productor')['cantidad'].sum().reset_index().sort_values('cantidad', ascending=False).head(10)
                fig_bar = px.bar(df_prod, x='productor', y='cantidad', title="Top 10 Productores en Cámara", color='cantidad')
                st.plotly_chart(fig_bar, use_container_width=True)

    # ----------------------------------------------------------
    # 4. STOCK PLAYA (GESTIÓN DE EMBARQUES Y RECEPCIÓN)
    # ----------------------------------------------------------
    elif selected == "4. Stock Playa":
        st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🚚 Control de Recepción - Playa</h1>", unsafe_allow_html=True)

        PATH_CSV_PLAYA = "procesados/stock playa.csv"

        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("🔄 Sincronizar desde CSV Playa", use_container_width=True):
                try:
                    df_csv_p = pd.read_csv(PATH_CSV_PLAYA, sep=';', encoding='utf-8-sig', engine='python')
                    df_csv_p.columns = [c.strip().upper() for c in df_csv_p.columns]
                    
                    df_para_db = pd.DataFrame()
                    df_para_db['id_orden'] = range(len(df_csv_p))
                    df_para_db['fecha'] = df_csv_p.get('FECHA', datetime.now().strftime('%Y-%m-%d'))
                    df_para_db['finca'] = df_csv_p.get('FINCA', 'Sin Dato')
                    df_para_db['destino'] = df_csv_p.get('DESTINO', 'NOUE')
                    df_para_db['bins'] = df_csv_p.get('BINS', 0).astype(int)
                    df_para_db['color_estimado'] = df_csv_p.get('COLOR_ESTIMADO', 'V')

                    with conectar_db() as conn:
                        df_para_db.to_sql('stock_playa', conn, if_exists='replace', index=False)
                    st.success(f"✅ Sincronización exitosa desde '{PATH_CSV_PLAYA}'")
                    st.rerun()
                except FileNotFoundError:
                    st.error(f"No se localizó el archivo: {PATH_CSV_PLAYA}")
                except Exception as e:
                    st.error(f"Error al sincronizar: {e}")

        with col_b:
            if st.button("➕ Nueva Entrada Manual (Fila)", use_container_width=True):
                try:
                    with conectar_db() as conn:
                        try:
                            ultimo = conn.execute("SELECT MAX(id_orden) FROM stock_playa").fetchone()[0]
                            nuevo_id = (ultimo + 1) if ultimo is not None else 0
                        except:
                            nuevo_id = 0
                        
                        conn.execute("""
                            INSERT INTO stock_playa (id_orden, fecha, finca, destino, bins, color_estimado)
                            VALUES (?, ?, 'NUEVA FINCA', 'UE', 0, 'V')
                        """, (nuevo_id, datetime.now().strftime('%Y-%m-%d')))
                        conn.commit()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al crear fila: {e}")

        try:
            with conectar_db() as conn:
                df_playa = pd.read_sql_query("SELECT * FROM stock_playa ORDER BY id_orden ASC", conn)

            st.markdown("### 📋 Planilla de Recepción")
            
            config_playa = {
                "id_orden": None,
                "fecha": st.column_config.TextColumn("📅 Fecha Arribo"),
                "finca": st.column_config.TextColumn("🚜 Finca / Frente"),
                "destino": st.column_config.SelectboxColumn("🌍 Destino", options=["UE", "USA", "NOUE"]),
                "bins": st.column_config.NumberColumn("📦 Cant. Bins", min_value=0),
                "color_estimado": st.column_config.SelectboxColumn("🎨 Color Est.", options=["VO", "V", "VC", "P", "A"])
            }

            df_editado_p = st.data_editor(
                df_playa,
                column_config=config_playa,
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
                key="editor_playa_final"
            )

            if st.button("💾 Guardar y Actualizar Respaldo CSV", use_container_width=True):
                try:
                    with conectar_db() as conn:
                        df_editado_p.to_sql('stock_playa', conn, if_exists='replace', index=False)
                    
                    df_editado_p.to_csv(PATH_CSV_PLAYA, sep=';', index=False, encoding='latin-1')
                    st.success("✅ Respaldo guardado correctamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

            st.divider()
            total_bins_playa = int(df_editado_p['bins'].sum())
            kilos_fijos_playa = total_bins_playa * 370
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"<div style='background-color: #eff6ff; padding: 15px; border-radius: 8px; border-left: 5px solid #1e40af;'><p style='margin:0; color:#1e40af; font-weight:bold;'>TOTAL BINS PLAYA</p><h2 style='margin:0;'>{total_bins_playa} Bins</h2></div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<div style='background-color: #f0fdf4; padding: 15px; border-radius: 8px; border-left: 5px solid #15803d;'><p style='margin:0; color:#15803d; font-weight:bold;'>KILOS BRUTOS ESTIMADOS</p><h2 style='margin:0;'>{kilos_fijos_playa:,} kg</h2></div>", unsafe_allow_html=True)

        except Exception:
            st.warning("⚠️ No hay datos cargados en el stock de playa.")
# ============================================================
# PRODUCCIÓN
# ============================================================
elif area == "Producción":
    import mod_produccion as prod_mod
    prod_mod.mostrar_produccion(guardar_datos_universal)


# ============================================================
# PERSONAL
# ============================================================
elif area == "Personal":
    pers_mod.mostrar_personal()
    


# ============================================================
# MUESTRAS
# ============================================================
elif area == "Muestras":
    import mod_produccion as prod_mod
    with st.sidebar:
        sub_muestras = option_menu(
            "Muestras",
            ["Gestión Preselección","Gestión Producción"],
            icons=["apple","box-seam"],
            menu_icon="clipboard-check",
            default_index=0
        )

    if sub_muestras == "Gestión Preselección":
        t_campo, t_romaneo, t_bins = st.tabs([
            "🗑️ Control Descarte/Campo","📊 Romaneo","🍱 Bins Terminados"
        ])

        with t_campo:
            campo_mod.vista_control_campo()

        with t_romaneo:
            rom_mod.vista_romaneo()

        with t_bins:
            st.subheader("📦 Registro de Bins Terminados")
            
            # --- 1. CONFIGURACIÓN DE RUTA ---
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            PATH_BINS_CSV = os.path.join(BASE_DIR, "procesados", "bines terminado.csv")

            # --- 2. FORMULARIO DE CARGA ---
            with st.form("form_bins_completos", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                
                with c1:
                    cod_bin       = st.text_input("Código Bin")
                    f_proceso     = st.date_input("Fecha de Proceso", datetime.now())
                    turno_b       = st.selectbox("Turno", [1, 2])
                    destino_b     = st.selectbox("Destino", ["USA", "UE", "NOUE"])
                    up_code       = st.text_input("UP")
                    finca_bin     = st.selectbox("Finca", LISTA_FINCAS, key="finca_bins_t")
                
                with c2:
                    remito_bin    = st.text_input("Remito")
                    f_cosecha_bin = st.date_input("Fecha de Cosecha")
                    leves_b       = st.number_input("Leves %", 0.0, 100.0, step=0.1)
                    menor_b       = st.number_input("Menor %", 0.0, 100.0, step=0.1)
                    # El cálculo de "Mayor" es automático (100 - leves - menor)
                    mayor_b       = round(100.0 - leves_b - menor_b, 2)
                    st.metric("Mayor (Auto)", f"{mayor_b}%")
                
                with c3:
                    # Lógica de calidad automática según destino
                    if destino_b == "USA":
                        calidad_final_b = st.selectbox("Calidad USA", ["Fancy", "Choice", "200"])
                    else:
                        # Si Menor > 25 es 300, sino 200 (según tus reglas)
                        calidad_final_b = "300" if menor_b > 25 else "200"
                        st.metric("Calidad (Auto)", calidad_final_b)
                    
                    porc_a_b = st.number_input("Porcentaje A %", 0.0, 100.0, step=0.1)
                    # El B% se calcula solo al instante
                    porc_b_b = round(100.0 - porc_a_b, 2)
                    st.write(f"**B% calculado:** {porc_b_b}%")
                
                obs_b = st.text_area("Observaciones")

                if st.form_submit_button("💾 Guardar Bin Terminado"):
                    try:
                        nuevo_bin = {
                            "codigo": cod_bin, "fecha": str(f_proceso), "turno": turno_b, 
                            "destino": destino_b, "up": up_code, "finca": finca_bin, 
                            "remito": remito_bin, "leves": leves_b, "menor": menor_b, 
                            "mayor": mayor_b, "calidad": calidad_final_b, "porc_a": porc_a_b, 
                            "porc_b": porc_b_b, "fecha_cosecha": str(f_cosecha_bin), "observaciones": obs_b
                        }
                        
                        # Guardar en Base de Datos
                        with conectar_db() as conn:
                            pd.DataFrame([nuevo_bin]).to_sql('bins_terminados', conn, if_exists='append', index=False)
                            # Actualizar CSV
                            df_total = pd.read_sql_query("SELECT * FROM bins_terminados", conn)
                            df_total.to_csv(PATH_BINS_CSV, sep=';', index=False, encoding='latin-1')
                        
                        st.success("✅ Bin guardado y CSV actualizado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

            # --- 3. VISUALIZACIÓN Y PORCENTAJES DIRECTOS ---
            st.divider()
            st.subheader("📊 Resumen de Bins Registrados")

            if os.path.exists(PATH_BINS_CSV):
                df_bins = pd.read_csv(PATH_BINS_CSV, sep=';', encoding='latin-1')
                
                if not df_bins.empty:
                    # Cálculo de porcentaje de calidad directamente
                    total_bins = len(df_bins)
                    st.write(f"Total de bines procesados: **{total_bins}**")
                    
                    # Editor para corregir datos rápido
                    df_editado = st.data_editor(
                        df_bins,
                        use_container_width=True,
                        hide_index=True,
                        num_rows="dynamic",
                        key="editor_bines_terminados"
                    )
                    
                    if st.button("🔄 Sincronizar Cambios de Tabla"):
                        df_editado.to_csv(PATH_BINS_CSV, sep=';', index=False, encoding='latin-1')
                        with conectar_db() as conn:
                            df_editado.to_sql('bins_terminados', conn, if_exists='replace', index=False)
                        st.success("✅ Cambios sincronizados.")
                        st.rerun()
                else:
                    st.info("No hay bines registrados todavía.")
            else:
                st.warning("El archivo de bines no existe. Cargá el primero arriba.")
# ============================================================
# REPORTES
# ============================================================
elif area == "Reportes":
    import mod_reportes as rep
    rep.vista_exportar_datos()


# ============================================================
# IMPORTAR HISTORIAL
# ============================================================
elif area == "Importar Historial":
   imp.modulo_importar()


# ============================================================
# CONFIGURACIÓN
# ============================================================
elif area == "Configuracion":
    st.title("⚙️ Panel de Control")
    if st.session_state.rol_actual == "admin":
        st.success(f"Sesión de Administrador: {st.session_state.user_actual}")
        mu.panel_admin()
    else:
        st.error("🚫 Acceso Denegado. Solo el Administrador puede gestionar usuarios.")



# ============================================================
# PANEL GENRENCIAL
# =======================================================
elif area == "Panel Gerencial":
    # Aquí llamamos a la función que está en mod_gerencia.py
    mostrar_dashboard_gerencial()
     

     # BOTÓN PARA LIBERAR ARCHIVOS (Solo para vos)
if st.sidebar.button("🔓 Liberar Excel (Reset)"):
    st.warning("Liberando bloqueos... La app se reiniciará.")
    import os
    import signal
    # Esto reinicia el proceso actual de la app y libera los archivos
    os.kill(os.getpid(), signal.SIGTERM)


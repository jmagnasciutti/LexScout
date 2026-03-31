import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import tempfile
import google.generativeai as genai

# --- 1. CONFIGURACIÓN Y ESTÉTICA ---
st.set_page_config(page_title="LexScout", page_icon="⚖️", layout="wide")
ADMIN_USER = "jose_luis" 

st.markdown("""
    <style>
    header, footer, #MainMenu {visibility: hidden !important;}
    .stDeployButton {display:none !important;}
    [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {display: none !important;}
    .stApp { background-color: #ecedf0; }
    h1, h2, h3 { color: #0c1b33 !important; font-family: 'Times New Roman', serif; font-weight: 800; }
    [data-testid="stSidebar"] { background-color: #081222; border-right: 5px solid #a6894a; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    div.stButton > button {
        background-color: #ffffff; color: #081222; border: 2px solid #a6894a;
        font-weight: 700; transition: 0.3s;
    }
    div.stButton > button:hover { background-color: #081222; color: #ffffff; }
    .resumen-card {
        background-color: #ffffff; padding: 30px; border-radius: 4px;
        border-top: 10px solid #a6894a; box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de conexión: {e}"); st.stop()

# --- 3. LOGIN ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center; margin-top: 50px;'>L E X S C O U T</h1>", unsafe_allow_html=True)
    df_socios = conn.read(worksheet="usuarios", ttl=0)
    col1, col2, col3 = st.columns([1,1.2,1])
    with col2:
        u_in = st.text_input("Usuario")
        c_in = st.text_input("Clave", type="password")
        if st.button("INGRESAR", use_container_width=True):
            u_f = u_in.strip().lower()
            match = df_socios[(df_socios['usuario'].str.strip().str.lower() == u_f) & (df_socios['clave'].astype(str).str.strip() == c_in.strip())]
            if not match.empty:
                st.session_state['autenticado'], st.session_state['usuario_actual'] = True, u_f
                st.rerun()
            else: st.error("Credenciales incorrectas.")
    st.stop()

# --- 4. CARGA DE DATOS ---
df_clientes = conn.read(worksheet="clientes", ttl=0).fillna("")
if 'estado' not in df_clientes.columns: df_clientes['estado'] = 'Activo'

# --- 5. INTERFAZ PRINCIPAL ---
st.markdown("<h1 style='text-align: center; letter-spacing: 5px;'>LEXSCOUT</h1>", unsafe_allow_html=True)
st.divider()

col_p, col_d = st.columns([2.8, 1], gap="medium")

with col_d:
    st.markdown("### 🗄️ EXPEDIENTES")
    vista = st.radio("Filtro:", ["Activos", "Archivados"], horizontal=True, label_visibility="collapsed")
    df_f = df_clientes[df_clientes['estado'].astype(str).str.lower() == ('activo' if vista == "Activos" else 'archivado')]
    for idx, row in df_f.iterrows():
        if st.button(f"📁 {row['nombre_cliente']}", key=f"btn_{idx}", use_container_width=True):
            st.session_state['cliente_sel'] = row['nombre_cliente']
            st.rerun()

with col_p:
    if 'cliente_sel' in st.session_state:
        c_sel = st.session_state['cliente_sel']
        datos = df_clientes[df_clientes['nombre_cliente'] == c_sel].iloc[0]
        st.markdown(f"## Expediente: {c_sel}")
        
        res_txt = datos['resumen_caso'] if datos['resumen_caso'] != "" else "⚠️ Sin sinopsis estratégica cargada."
        st.markdown(f"""<div class="resumen-card"><h4>SINOPSIS ESTRATÉGICA</h4><p>{res_txt}</p><hr><p><b>VENCIMIENTO:</b> {datos.get('vencimiento', 'Sin fecha')}</p></div>""", unsafe_allow_html=True)
        
        if datos.get('Link Notebooklm') != "":
            st.link_button("📜 ABRIR LIBRO EN NOTEBOOKLM", datos['Link Notebooklm'], use_container_width=True)
        
        st.divider()

        # --- MOTOR IA ---
        st.markdown("### 📥 ANALIZAR ACTUACIÓN")
        archivo = st.file_uploader("Subir PDF", type="pdf", label_visibility="collapsed")
        if archivo:
            if st.button("🚀 GENERAR SINOPSIS CON IA", use_container_width=True):
                with st.spinner("⚖️ Analizando..."):
                    try:
                        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                        # PROBAMOS ESTE NOMBRE QUE ES EL MÁS ESTABLE EN 2026
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            tmp.write(archivo.getvalue()); t_path = tmp.name
                        
                        doc_ia = genai.upload_file(path=t_path, mime_type="application/pdf")
                        response = model.generate_content(["Resumí este documento judicial en 4 líneas clave.", doc_ia])
                        
                        df_db = conn.read(worksheet="clientes", ttl=0)
                        df_db.loc[df_db['nombre_cliente'] == c_sel, 'resumen_caso'] = response.text
                        conn.update(worksheet="clientes", data=df_db)
                        
                        st.success("✅ Sinopsis actualizada.")
                        os.remove(t_path)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Falla técnica: {e}")
    else:
        st.info("Seleccione un expediente.")

# --- 6. BARRA LATERAL ---
with st.sidebar:
    st.markdown(f"👤 **Usuario:** {st.session_state['usuario_actual']}")
    if st.session_state['usuario_actual'] == ADMIN_USER:
        st.markdown("### ⚙️ ADMINISTRACIÓN")
        with st.expander("➕ NUEVO"):
            n = st.text_input("Nombre")
            l = st.text_input("Notebook Link")
            if st.button("REGISTRAR"):
                new = pd.DataFrame([{"nombre_cliente": n, "Link Notebooklm": l, "estado": "Activo"}])
                conn.update(worksheet="clientes", data=pd.concat([df_clientes, new], ignore_index=True))
                st.rerun()
        if 'cliente_sel' in st.session_state:
            if st.button("📦 ARCHIVAR", use_container_width=True):
                df_clientes.loc[df_clientes['nombre_cliente'] == c_sel, 'estado'] = 'Archivado'
                conn.update(worksheet="clientes", data=df_clientes); st.rerun()
    if st.button("Cerrar Sesión"):
        st.session_state['autenticado'] = False; st.rerun()

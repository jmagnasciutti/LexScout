import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import tempfile
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="LexScout", page_icon="⚖️", layout="wide")
ADMIN_USER = "jose_luis" 

st.markdown("""
    <style>
    header, footer, #MainMenu {visibility: hidden !important;}
    .stDeployButton {display:none !important;}
    .stApp { background-color: #ecedf0; }
    h1, h2, h3 { color: #0c1b33 !important; font-family: 'Times New Roman', serif; }
    [data-testid="stSidebar"] { background-color: #081222; border-right: 5px solid #a6894a; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    div.stButton > button {
        background-color: #ffffff; color: #081222; border: 2px solid #a6894a;
        font-weight: 700; transition: 0.3s;
    }
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

# --- 5. INTERFAZ ---
st.markdown("<h1 style='text-align: center; letter-spacing: 5px;'>LEXSCOUT</h1>", unsafe_allow_html=True)
st.divider()

col_principal, col_derecha = st.columns([2.8, 1])

with col_derecha:
    st.markdown("### 🗄️ EXPEDIENTES")
    for idx, row in df_clientes.iterrows():
        if st.button(f"📁 {row['nombre_cliente']}", key=f"btn_{idx}", use_container_width=True):
            st.session_state['cliente_sel'] = row['nombre_cliente']
            st.rerun()

with col_principal:
    if 'cliente_sel' in st.session_state:
        c_sel = st.session_state['cliente_sel']
        datos = df_clientes[df_clientes['nombre_cliente'] == c_sel].iloc[0]
        
        st.markdown(f"## Expediente: {c_sel}")
        res_display = datos['resumen_caso'] if datos['resumen_caso'] != "" else "⚠️ Sin sinopsis estratégica."
        
        st.markdown(f"""
            <div class="resumen-card">
                <h4 style='margin-top:0;'>SINOPSIS ESTRATÉGICA</h4>
                <p style='font-size: 16px; line-height: 1.6;'>{res_display}</p>
                <hr>
                <p style='color: #a6894a;'><b>VENCIMIENTO:</b> {datos.get('vencimiento', 'Sin fecha')}</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.divider()

        # --- MOTOR DE IA ---
        st.markdown("### 📥 ANALIZAR DOCUMENTO")
        archivo = st.file_uploader("Subir PDF", type="pdf", label_visibility="collapsed")
        
        if archivo:
            if st.button("🚀 GENERAR SINOPSIS CON IA", use_container_width=True):
                with st.spinner("⚖️ Analizando con Gemini 1.5 Flash..."):
                    try:
                        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                        model = genai.GenerativeModel('gemini-1.5-flash-latest')
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            tmp.write(archivo.getvalue())
                            t_path = tmp.name
                        
                        doc_ia = genai.upload_file(path=t_path, mime_type="application/pdf")
                        prompt = "Analizá este documento judicial argentino y resumí en 4 líneas los puntos estratégicos clave. Al final poné 'FECHA: DD/MM/AAAA' si hay un vencimiento, sino 'FECHA: Sin fecha'."
                        response = model.generate_content([prompt, doc_ia])
                        
                        # Guardar resultado
                        df_db = conn.read(worksheet="clientes", ttl=0)
                        df_db.loc[df_db['nombre_cliente'] == c_sel, 'resumen_caso'] = response.text
                        conn.update(worksheet="clientes", data=df_db)
                        
                        st.success("✅ ¡Análisis guardado!")
                        os.remove(t_path)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ ERROR: {e}")
    else:
        st.info("Seleccioná un expediente para comenzar.")

# --- 6. BARRA LATERAL ---
with st.sidebar:
    st.markdown(f"👤 **Usuario:** {st.session_state.get('usuario_actual', '')}")
    if st.button("Cerrar Sesión"):
        st.session_state['autenticado'] = False
        st.rerun()

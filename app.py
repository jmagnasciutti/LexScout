import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import tempfile
import google.generativeai as genai

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="LexScout", page_icon="⚖️", layout="wide")
ADMIN_USER = "jose_luis" 

# (Mantenemos tu CSS igual...)
st.markdown("<style>header, footer, #MainMenu {visibility: hidden !important;} .stApp { background-color: #ecedf0; } .resumen-card { background-color: #ffffff; padding: 30px; border-radius: 4px; border-top: 10px solid #a6894a; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 25px; }</style>", unsafe_allow_html=True)

# --- CONEXIÓN ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_clientes = conn.read(worksheet="clientes", ttl=0)
except Exception as e:
    st.error(f"Error de conexión con Excel: {e}"); st.stop()

# --- LOGIN (Simplificado para la prueba) ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
if not st.session_state['autenticado']:
    # ... (Tu código de login que ya funciona)
    st.session_state['autenticado'] = True # Solo para testear rápido
    st.rerun()

# --- INTERFAZ ---
st.title("LEXSCOUT")

col_principal, col_derecha = st.columns([2.5, 1])

with col_derecha:
    st.markdown("### 🗄️ EXPEDIENTES")
    for idx, row in df_clientes.iterrows():
        if st.button(f"📁 {row['nombre_cliente']}", key=f"btn_{idx}"):
            st.session_state['cliente_sel'] = row['nombre_cliente']
            st.rerun()

with col_principal:
    if 'cliente_sel' in st.session_state:
        c_sel = st.session_state['cliente_sel']
        datos = df_clientes[df_clientes['nombre_cliente'] == c_sel].iloc[0]
        
        st.markdown(f"## Expediente: {c_sel}")
        
        # FICHA
        st.markdown(f"""<div class="resumen-card"><h4>SINOPSIS ESTRATÉGICA</h4><p>{datos.get('resumen_caso', 'Sin datos')}</p></div>""", unsafe_allow_html=True)
        
        st.divider()
        
        # MOTOR IA
        st.markdown("### 📥 ANALIZAR DOCUMENTO")
        archivo = st.file_uploader("Subir PDF", type="pdf")
        
        if archivo:
            if st.button("🚀 GENERAR SINOPSIS"):
                try:
                    with st.spinner("Analizando con Gemini..."):
                        # 1. Configurar IA
                        if "GEMINI_API_KEY" not in st.secrets:
                            st.error("Falta la clave GEMINI_API_KEY en Secrets.")
                            st.stop()
                            
                        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        # 2. Procesar Archivo
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            tmp.write(archivo.getvalue())
                            t_path = tmp.name
                        
                        # 3. Subir y Generar
                        doc_ia = genai.upload_file(path=t_path, mime_type="application/pdf")
                        prompt = "Resume este documento judicial en 4 líneas destacando lo procesalmente relevante para un abogado."
                        response = model.generate_content([prompt, doc_ia])
                        
                        # 4. Guardar
                        df_clientes.loc[df_clientes['nombre_cliente'] == c_sel, 'resumen_caso'] = response.text
                        conn.update(worksheet="clientes", data=df_clientes)
                        
                        st.success("¡Sinopsis actualizada!")
                        os.remove(t_path)
                        st.rerun()
                except Exception as e:
                    st.error(f"Error detallado: {e}")

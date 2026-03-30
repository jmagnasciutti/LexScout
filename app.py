import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import tempfile
from datetime import datetime

# 1. CONFIGURACIÓN Y ESTÉTICA PROFESIONAL
st.set_page_config(page_title="LexScout", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    header, footer, #MainMenu {visibility: hidden !important;}
    .stDeployButton {display:none !important;}
    [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {display: none !important;}
    
    .stApp { background-color: #ecedf0; }
    h1, h2, h3 { color: #0c1b33 !important; font-family: 'Times New Roman', serif; font-weight: 800; }

    [data-testid="stSidebar"] {
        background-color: #081222;
        border-right: 5px solid #a6894a;
    }
    [data-testid="stSidebar"] * { color: #ffffff !important; }

    div.stButton > button {
        background-color: #ffffff;
        color: #081222;
        border: 2px solid #a6894a;
        font-weight: 700;
        transition: 0.3s;
    }
    div.stButton > button:hover { background-color: #081222; color: #ffffff; }

    .resumen-card {
        background-color: #ffffff;
        padding: 30px;
        border-radius: 4px;
        border-top: 10px solid #a6894a;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }
    </style>
    """, unsafe_allow_html=True)

from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# --- CONEXIÓN ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de conexión: {e}"); st.stop()

# 2. ACCESO PRIVADO
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center; margin-top: 50px;'>L E X S C O U T</h1>", unsafe_allow_html=True)
    df_socios = conn.read(worksheet="usuarios", ttl=0)
    col1, col2, col3 = st.columns([1,1.2,1])
    with col2:
        u = st.text_input("Usuario"); c = st.text_input("Clave", type="password")
        if st.button("INGRESAR", use_container_width=True):
            if not df_socios[(df_socios['usuario'] == u) & (df_socios['clave'] == c)].empty:
                st.session_state['autenticado'], st.session_state['usuario_actual'] = True, u
                st.rerun()
            else: st.error("Acceso Denegado.")
    st.stop()

# --- CARGA DE DATOS ---
df_clientes = conn.read(worksheet="clientes", ttl=0)
if 'estado' not in df_clientes.columns: df_clientes['estado'] = 'Activo'

# 3. INTERFAZ
st.markdown("<h1 style='text-align: center; letter-spacing: 5px;'>LEXSCOUT</h1>", unsafe_allow_html=True)
st.divider()

col_principal, col_derecha = st.columns([2.8, 1], gap="medium")

with col_derecha:
    st.markdown("### 🗄️ EXPEDIENTES")
    vista = st.radio("Filtro:", ["Activos", "Archivados"], horizontal=True, label_visibility="collapsed")
    df_filtrado = df_clientes[df_clientes['estado'].fillna('Activo') == ('Activo' if vista == "Activos" else 'Archivado')]
    
    for idx, row in df_filtrado.iterrows():
        if st.button(f"📁 {row['nombre_cliente']}", key=f"btn_{idx}", use_container_width=True):
            st.session_state['cliente_sel'] = row['nombre_cliente']
            st.rerun()

    if vista == "Activos" and 'vencimiento' in df_clientes.columns:
        st.divider()
        st.markdown("### ⏳ ALERTAS")
        hoy = datetime.now()
        for _, row in df_filtrado.iterrows():
            if pd.notna(row['vencimiento']):
                try:
                    venc = datetime.strptime(str(row['vencimiento']), "%d/%m/%Y")
                    dias = (venc - hoy).days
                    if 0 <= dias <= 7: st.error(f"**{row['nombre_cliente']}**\nVence en {dias} días.")
                except: pass

with col_principal:
    if 'cliente_sel' in st.session_state:
        cliente_actual = st.session_state['cliente_sel']
        datos_c = df_clientes[df_clientes['nombre_cliente'] == cliente_actual].iloc[0]
        
        st.markdown(f"## Expediente: {cliente_actual}")
        
        # FICHA DE EXPEDIENTE
        resumen_txt = datos_c['resumen_caso'] if 'resumen_caso' in df_clientes.columns and pd.notna(datos_c['resumen_caso']) else "Pendiente de análisis. Suba un documento abajo."
        venc_txt = datos_c['vencimiento'] if 'vencimiento' in df_clientes.columns and pd.notna(datos_c['vencimiento']) else "Sin fecha."

        st.markdown(f"""
            <div class="resumen-card">
                <h4 style='margin-top:0; color:#081222;'>SINOPSIS ESTRATÉGICA</h4>
                <p style='color: #2d3748; line-height: 1.8; font-size: 16px;'>{resumen_txt}</p>
                <hr style='border: 0.5px solid #eee; margin: 20px 0;'>
                <p style='font-size: 14px; color: #a6894a;'><b>VENCIMIENTO DETECTADO:</b> {venc_txt}</p>
            </div>
        """, unsafe_allow_html=True)
        
        link_nb = datos_c.get('Link Notebooklm')
        if pd.notna(link_nb):
            st.link_button("📜 ABRIR LIBRO EN NOTEBOOKLM", link_nb, use_container_width=True)
        
        st.divider()

        # MOTOR DE IA: GENERACIÓN DE SINOPSIS
        st.markdown("### 📥 ANALIZAR PIEZA CLAVE")
        st.caption("Suba el PDF principal para que la IA redacte automáticamente el resumen y detecte fechas clave.")
        
        archivo = st.file_uploader("Subir PDF", type="pdf", label_visibility="collapsed")
        
        if archivo and "OPENAI_API_KEY" in st.secrets:
            with st.spinner("⚖️ IA LexScout analizando pieza procesal..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(archivo.getvalue())
                    tmp_path = tmp.name
                
                try:
                    loader = PyPDFLoader(tmp_path)
                    docs = loader.load()
                    
                    llm = ChatOpenAI(model="gpt-4o-mini", api_key=st.secrets["OPENAI_API_KEY"], temperature=0)
                    prompt_ia = ChatPromptTemplate.from_template(
                        "Eres un secretario judicial experto. Analiza este documento y extrae:\n"
                        "1. Resumen ejecutivo de la situación (máximo 4 líneas).\n"
                        "2. Próxima fecha de vencimiento (formato DD/MM/AAAA).\n"
                        "Responde SOLO en JSON con las llaves 'resumen' y 'vencimiento'.\n\n"
                        "Documento: {context}"
                    )
                    
                    chain = prompt_ia | llm | JsonOutputParser()
                    res = chain.invoke({"context": docs[0].page_content[:4500]})
                    
                    # ACTUALIZACIÓN EN EL DATAFRAME Y EXCEL
                    if 'resumen_caso' not in df_clientes.columns: df_clientes['resumen_caso'] = ""
                    if 'vencimiento' not in df_clientes.columns: df_clientes['vencimiento'] = ""

                    df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'resumen_caso'] = res['resumen']
                    if res['vencimiento'] != "Sin fecha":
                        df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'vencimiento'] = res['vencimiento']
                    
                    conn.update(worksheet="clientes", data=df_clientes)
                    st.success("✅ ¡Ficha actualizada!")
                    os.remove(tmp_path)
                    st.rerun() # Esto actualiza la interfaz y muestra el resumen arriba
                except Exception as e:
                    st.error(f"Falla en el análisis automático: {e}")
    else:
        st.markdown("<div style='text-align:center; padding-top:100px; color:#aaa;'><h3>Seleccione un caso del archivo</h3></div>", unsafe_allow_html=True)

# 4. ADMINISTRACIÓN
with st.sidebar:
    st.markdown("### ⚙️ ADMINISTRACIÓN")
    with st.expander("➕ NUEVO EXPEDIENTE"):
        n = st.text_input("Nombre del Cliente")
        l = st.text_input("Link NotebookLM")
        if st.button("REGISTRAR"):
            if n:
                nueva = pd.DataFrame([{"nombre_cliente": n, "Link Notebooklm": l, "estado": "Activo"}])
                df_upd = pd.concat([df_clientes, nueva], ignore_index=True)
                conn.update(worksheet="clientes", data=df_upd)
                st.success("Registrado"); st.rerun()

    if 'cliente_sel' in st.session_state:
        st.divider()
        if st.button("📦 ARCHIVAR", use_container_width=True):
            df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'estado'] = 'Archivado'
            conn.update(worksheet="clientes", data=df_clientes)
            st.rerun()
        
        with st.expander("🚨 ELIMINAR"):
            if st.button("BORRAR DEFINITIVAMENTE", type="primary", use_container_width=True):
                df_f = df_clientes[df_clientes['nombre_cliente'] != cliente_actual]
                conn.update(worksheet="clientes", data=df_f)
                del st.session_state['cliente_sel']; st.rerun()

# Definimos quién es el administrador (tu usuario)
ADMIN_USER = "jose_luis" # Poné acá tu nombre de usuario exacto del Excel

with st.sidebar:
    st.markdown(f"👤 **Socio:** {st.session_state['usuario_actual']}")
    
    # SOLO VOS podés crear o borrar. Tu socio solo verá la lista.
    if st.session_state['usuario_actual'] == ADMIN_USER:
        st.markdown("### ⚙️ Panel de Control (Admin)")
        with st.expander("➕ Nuevo Expediente"):
            # ... (código para crear expediente)
            
        with st.expander("🚨 Zona de Peligro"):
            # ... (código para borrar expediente)
    else:
        # Lo que ve tu socio (Solo consulta)
        st.info("Modo: Consulta de Expedientes")

st.markdown("""
    <style>
    /* Oculta TODO lo que no es la App */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid="stToolbar"] {display: none;}
    [data-testid="stDecoration"] {display: none;}
    </style>
    """, unsafe_allow_html=True)

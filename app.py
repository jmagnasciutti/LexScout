import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import tempfile
from datetime import datetime

# 1. CONFIGURACIÓN Y BLINDAJE ESTÉTICO (FONDO GRIS Y OCULTAR HERRAMIENTAS)
st.set_page_config(page_title="LexScout", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    /* Ocultar rastro de Streamlit (Botones de edición, estrella, etc.) */
    header, footer, #MainMenu {visibility: hidden !important;}
    .stDeployButton {display:none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    
    /* Fondo Profesional Gris Piedra */
    .stApp { background-color: #ecedf0; }
    
    /* Tipografía de Bufete */
    h1, h2, h3 { 
        color: #0c1b33 !important; 
        font-family: 'Times New Roman', serif;
        font-weight: 800;
    }

    /* Barra Lateral Azul Medianoche */
    [data-testid="stSidebar"] {
        background-color: #081222;
        border-right: 5px solid #a6894a;
    }
    [data-testid="stSidebar"] * { color: #ffffff !important; }

    /* Botones Resaltados */
    div.stButton > button {
        background-color: #ffffff;
        color: #081222;
        border: 2px solid #a6894a;
        font-weight: 700;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color: #081222;
        color: #ffffff;
    }

    /* Ficha Judicial (Tarjeta) */
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

# --- DATOS ---
df_clientes = conn.read(worksheet="clientes", ttl=0)
if 'estado' not in df_clientes.columns: df_clientes['estado'] = 'Activo'

# 3. PANEL DE CONTROL
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
        
        # MOSTRAR RESUMEN (Aquí se verá el cambio tras la IA)
        res_actual = datos_c['resumen_caso'] if 'resumen_caso' in df_clientes.columns and pd.notna(datos_c['resumen_caso']) else "Pendiente de análisis. Suba un documento abajo."
        venc_actual = datos_c['vencimiento'] if 'vencimiento' in df_clientes.columns and pd.notna(datos_c['vencimiento']) else "Sin fecha."

        st.markdown(f"""
            <div class="resumen-card">
                <h4 style='margin-top:0; color:#081222;'>SINOPSIS ESTRATÉGICA</h4>
                <p style='color: #2d3748; line-height: 1.8; font-size: 16px;'>{res_actual}</p>
                <hr style='border: 0.5px solid #eee; margin: 20px 0;'>
                <p style='font-size: 14px; color: #a6894a;'><b>VENCIMIENTO DETECTADO:</b> {venc_actual}</p>
            </div>
        """, unsafe_allow_html=True)
        
        if pd.notna(datos_c.get('Link Notebooklm')):
            st.link_button("📜 ABRIR LIBRO EN NOTEBOOKLM", datos_c['Link Notebooklm'], use_container_width=True)
        
        st.divider()

        # MOTOR DE IA: GENERACIÓN DE RESUMEN
        st.markdown("### 📥 ANALIZAR PIEZA PROCESAL")
        st.caption("Suba un PDF para que la IA redacte automáticamente el resumen en su base de datos.")
        
        archivo = st.file_uploader("Subir PDF", type="pdf", label_visibility="collapsed")
        
        if archivo and "OPENAI_API_KEY" in st.secrets:
            with st.spinner("⚖️ IA Generando resumen y actualizando planilla..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(archivo.getvalue()); tmp_path = tmp.name
                
                loader = PyPDFLoader(tmp_path)
                docs = loader.load()
                
                llm = ChatOpenAI(model="gpt-4o-mini", api_key=st.secrets["OPENAI_API_KEY"], temperature=0)
                prompt_ia = ChatPromptTemplate.from_template(
                    "Eres un secretario judicial experto. Analiza este documento y extrae:\n"
                    "1. Resumen ejecutivo del caso (máximo 4 líneas).\n"
                    "2. Fecha de vencimiento (DD/MM/AAAA).\n"
                    "Responde SOLO en JSON con llaves 'resumen' y 'vencimiento'.\n\n"
                    "Texto: {context}"
                )
                
                try:
                    chain = prompt_ia | llm | JsonOutputParser()
                    res = chain.invoke({"context": docs[0].page_content[:4500]})
                    
                    # ACTUALIZACIÓN FORZADA DEL EXCEL
                    if 'resumen_caso' not in df_clientes.columns: df_clientes['resumen_caso'] = ""
                    if 'vencimiento' not in df_clientes.columns: df_clientes['vencimiento'] = ""

                    df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'resumen_caso'] = res['resumen']
                    if res['vencimiento'] != "Sin fecha":
                        df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'vencimiento'] = res['vencimiento']
                    
                    conn.update(worksheet="clientes", data=df_clientes)
                    st.success("✅ ¡Base de datos actualizada!")
                    os.remove(tmp_path)
                    st.rerun() # ESTO FUERZA A QUE APAREZCA EL RESUMEN ARRIBA
                except Exception as e:
                    st.error(f"Falla en el análisis: {e}")
    else:
        st.markdown("<div style='text-align:center; padding-top:100px; color:#aaa;'><h3>Seleccione un caso para operar</h3></div>", unsafe_allow_html=True)

# 4. ADMINISTRACIÓN
with st.sidebar:
    st.markdown("### ⚙️ ADMIN")
    with st.expander("➕ NUEVO EXPEDIENTE"):
        n = st.text_input("Cliente")
        l = st.text_input("Link Notebook")
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
            if st.button("BORRAR AHORA", type="primary", use_container_width=True):
                df_f = df_clientes[df_clientes['nombre_cliente'] != cliente_actual]
                conn.update(worksheet="clientes", data=df_f)
                del st.session_state['cliente_sel']; st.rerun()

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import tempfile
from datetime import datetime

# 1. CONFIGURACIÓN Y BLINDAJE DE INTERFAZ (OCULTAR HERRAMIENTAS)
st.set_page_config(page_title="LexScout", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    /* Ocultar barra superior, menús y botones de edición de Streamlit */
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    #MainMenu {visibility: hidden !important;}
    .stDeployButton {display:none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}
    button[title="View source"] {display: none !important;}
    
    /* Fondo Profesional (Gris Piedra Suave) */
    .stApp {
        background-color: #ecedf0;
    }
    
    /* Tipografías Legales */
    h1, h2, h3 { 
        color: #0c1b33 !important; 
        font-family: 'Times New Roman', serif;
        font-weight: 800;
    }

    /* Barra Lateral (Azul Medianoche Profundo) */
    [data-testid="stSidebar"] {
        background-color: #081222;
        border-right: 5px solid #a6894a; /* Borde Oro Viejo */
    }
    [data-testid="stSidebar"] * { color: #ffffff !important; }

    /* BOTONES RESALTADOS (Contraste Alto) */
    div.stButton > button {
        background-color: #ffffff;
        color: #081222;
        border: 2px solid #a6894a;
        border-radius: 4px;
        font-weight: 700;
        height: 3em;
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:hover {
        background-color: #081222;
        color: #ffffff;
        border: 2px solid #ffffff;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }

    /* Tarjeta de Expediente (Diseño de Ficha Judicial) */
    .resumen-card {
        background-color: #ffffff;
        padding: 35px;
        border-radius: 5px;
        border-top: 12px solid #a6894a;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }
    </style>
    """, unsafe_allow_html=True)

from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# --- CONEXIÓN A BASE DE DATOS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error crítico de conexión: {e}"); st.stop()

# 2. ACCESO PRIVADO
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center; margin-top: 50px;'>L E X S C O U T</h1>", unsafe_allow_html=True)
    df_socios = conn.read(worksheet="usuarios", ttl=0)
    col1, col2, col3 = st.columns([1,1.2,1])
    with col2:
        u = st.text_input("Usuario Autorizado"); c = st.text_input("Clave de Acceso", type="password")
        if st.button("INGRESAR AL ESTUDIO", use_container_width=True):
            if not df_socios[(df_socios['usuario'] == u) & (df_socios['clave'] == c)].empty:
                st.session_state['autenticado'], st.session_state['usuario_actual'] = True, u
                st.rerun()
            else: st.error("Credenciales Inválidas.")
    st.stop()

# --- CARGA DE EXPEDIENTES ---
df_clientes = conn.read(worksheet="clientes", ttl=0)
if 'estado' not in df_clientes.columns: df_clientes['estado'] = 'Activo'

# 3. INTERFAZ DE TRABAJO
st.markdown("<h1 style='text-align: center; letter-spacing: 6px; margin-bottom: 0;'>LEXSCOUT</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #4a5568; font-size: 14px; margin-top: -10px;'>GESTIÓN JURÍDICA INTEGRAL</p>", unsafe_allow_html=True)

col_principal, col_derecha = st.columns([2.8, 1], gap="medium")

with col_derecha:
    st.markdown("### 🗄️ ARCHIVO")
    vista = st.radio("Filtrar por:", ["Activos", "Archivados"], horizontal=True, label_visibility="collapsed")
    df_filtrado = df_clientes[df_clientes['estado'].fillna('Activo') == ('Activo' if vista == "Activos" else 'Archivado')]
    
    st.markdown("---")
    for idx, row in df_filtrado.iterrows():
        if st.button(f"📁 {row['nombre_cliente']}", key=f"btn_{idx}", use_container_width=True):
            st.session_state['cliente_sel'] = row['nombre_cliente']
    
    st.divider()
    if vista == "Activos" and 'vencimiento' in df_clientes.columns:
        st.markdown("### ⏳ ALERTAS")
        hoy = datetime.now()
        for _, row in df_filtrado.iterrows():
            if pd.notna(row['vencimiento']):
                try:
                    venc = datetime.strptime(str(row['vencimiento']), "%d/%m/%Y")
                    dias = (venc - hoy).days
                    if 0 <= dias <= 7:
                        st.error(f"**Vence en {dias} días:**\n{row['nombre_cliente']}")
                except: pass

with col_principal:
    if 'cliente_sel' in st.session_state:
        cliente_actual = st.session_state['cliente_sel']
        datos_c = df_clientes[df_clientes['nombre_cliente'] == cliente_actual].iloc[0]
        
        st.markdown(f"## Expediente: {cliente_actual}")
        
        # FICHA TÉCNICA DINÁMICA
        resumen_act = datos_c['resumen_caso'] if 'resumen_caso' in df_clientes.columns and pd.notna(datos_c['resumen_caso']) else "Pendiente de análisis. Suba un documento para generar la sinopsis."
        venc_act = datos_c['vencimiento'] if 'vencimiento' in df_clientes.columns and pd.notna(datos_c['vencimiento']) else "Sin fecha detectada."
        
        st.markdown(f"""
            <div class="resumen-card">
                <h4 style='margin-top:0; color:#081222;'>SINOPSIS ESTRATÉGICA</h4>
                <p style='color: #2d3748; line-height: 1.8; font-size: 16px;'>{resumen_act}</p>
                <hr style='border: 0.5px solid #e2e8f0; margin: 25px 0;'>
                <p style='font-size: 14px; color: #a6894a;'><b>CALENDARIO JUDICIAL:</b> Vencimiento estimado para el <b>{venc_act}</b></p>
            </div>
        """, unsafe_allow_html=True)
        
        link_nb = datos_c['Link Notebooklm'] if 'Link Notebooklm' in df_clientes.columns else None
        if pd.notna(link_nb):
            st.link_button("📜 ABRIR LIBRO COMPLETO (NOTEBOOKLM)", link_nb, use_container_width=True)
        
        st.divider()
        
        # MOTOR DE SINCRONIZACIÓN POR IA
        st.markdown("### 📥 ACTUALIZAR EXPEDIENTE")
        st.caption("Al cargar un PDF, la IA extraerá automáticamente el resumen y las fechas clave para la base de datos.")
        
        archivo = st.file_uploader("Subir pieza procesal", type="pdf", label_visibility="collapsed")
        if archivo and "OPENAI_API_KEY" in st.secrets:
            with st.spinner("⚖️ IA LexScout analizando y actualizando planilla..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(archivo.getvalue()); tmp_path = tmp.name
                
                loader = PyPDFLoader(tmp_path)
                docs = loader.load()
                
                # Configuramos IA para extracción de datos estructurados
                llm = ChatOpenAI(model="gpt-4o-mini", api_key=st.secrets["OPENAI_API_KEY"], temperature=0)
                prompt_ia = ChatPromptTemplate.from_template(
                    "Eres un secretario judicial experto. Analiza este fragmento de un expediente y extrae:\n"
                    "1. Un resumen ejecutivo del estado del proceso (máximo 4 líneas).\n"
                    "2. La fecha de vencimiento o hito procesal más próximo (formato DD/MM/AAAA).\n"
                    "Responde únicamente en formato JSON con las llaves 'resumen' y 'vencimiento'.\n\n"
                    "Texto: {context}"
                )
                
                chain = prompt_ia | llm | JsonOutputParser()
                # Analizamos las primeras 4000 palabras (suficiente para la mayoría de escritos)
                res = chain.invoke({"context": docs[0].page_content[:4500]})
                
                # GUARDAR EN EL DATAFRAME Y SUBIR A GOOGLE SHEETS
                if 'resumen_caso' not in df_clientes.columns: df_clientes['resumen_caso'] = ""
                if 'vencimiento' not in df_clientes.columns: df_clientes['vencimiento'] = ""

                df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'resumen_caso'] = res['resumen']
                if res['vencimiento'] != "Sin fecha":
                    df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'vencimiento'] = res['vencimiento']
                
                conn.update(worksheet="clientes", data=df_clientes)
                st.success("✅ Base de datos actualizada con éxito.")
                os.remove(tmp_path)
                st.rerun() # Reinicio para mostrar los nuevos datos arriba
    else:
        st.markdown("<div style='text-align:center; padding-top:100px; color:#718096;'><h3>SISTEMA OPERATIVO</h3><p>Seleccione un expediente del archivo lateral para comenzar.</p></div>", unsafe_allow_html=True)

# 4. ADMINISTRACIÓN
with st.sidebar:
    st.markdown("### ⚙️ ADMINISTRACIÓN")
    with st.expander("➕ NUEVO EXPEDIENTE"):
        n = st.text_input("Nombre del Cliente")
        l = st.text_input("Link NotebookLM")
        if st.button("REGISTRAR"):
            if n:
                nueva_f = pd.DataFrame([{"nombre_cliente": n, "Link Notebooklm": l, "estado": "Activo"}])
                df_upd = pd.concat([df_clientes, nueva_f], ignore_index=True)
                conn.update(worksheet="clientes", data=df_upd)
                st.success("Registrado"); st.rerun()

    if 'cliente_sel' in st.session_state:
        st.divider()
        if st.button("📦 ARCHIVAR CASO", use_container_width=True):
            df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'estado'] = 'Archivado'
            conn.update(worksheet="clientes", data=df_clientes)
            st.rerun()
        
        with st.expander("🚨 ELIMINACIÓN"):
            if st.button("BORRAR DEFINITIVAMENTE", type="primary", use_container_width=True):
                df_f = df_clientes[df_clientes['nombre_cliente'] != cliente_actual]
                conn.update(worksheet="clientes", data=df_f)
                del st.session_state['cliente_sel']; st.rerun()

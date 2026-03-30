import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import tempfile
from datetime import datetime
import json

# 1. CONFIGURACIÓN Y OCULTAMIENTO DE INTERFAZ STREAMLIT
st.set_page_config(page_title="LexScout", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    /* Ocultar barra de herramientas de Streamlit (Share, Star, Deploy, etc.) */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid="stToolbar"] {display: none;}
    
    /* Fondo de página profesional (Gris Hueso) */
    .stApp {
        background-color: #f1f3f5;
    }
    
    /* Títulos y fuentes */
    h1, h2, h3 { 
        color: #1e3a8a !important; 
        font-family: 'Playfair Display', serif; 
        font-weight: 700;
        letter-spacing: -1px;
    }

    /* Barra lateral estilo Bufete */
    [data-testid="stSidebar"] {
        background-color: #1a2a44;
        border-right: 3px solid #c5a059;
    }
    [data-testid="stSidebar"] * { color: #e5e7eb !important; }

    /* Tarjetas de Expediente */
    .resumen-card {
        background-color: white;
        padding: 25px;
        border-radius: 8px;
        border-left: 8px solid #c5a059;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        margin-bottom: 30px;
    }

    /* Botones de navegación derecha */
    div.stButton > button {
        border: 1px solid #1e3a8a;
        color: #1e3a8a;
        background-color: white;
        font-size: 14px;
        font-weight: 500;
        padding: 10px;
        border-radius: 4px;
        transition: 0.2s;
    }
    div.stButton > button:hover {
        background-color: #1e3a8a;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import JsonOutputParser # Para extraer datos estructurados

# --- CONEXIÓN ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de sistema: {e}"); st.stop()

# 2. LOGIN (Tu llave de acceso)
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center;'>L E X S C O U T</h1>", unsafe_allow_html=True)
    df_socios = conn.read(worksheet="usuarios", ttl=0)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        u = st.text_input("Credencial"); c = st.text_input("Contraseña", type="password")
        if st.button("Acceder al Estudio", use_container_width=True):
            if not df_socios[(df_socios['usuario'] == u) & (df_socios['clave'] == c)].empty:
                st.session_state['autenticado'] = True; st.session_state['usuario_actual'] = u; st.rerun()
            else: st.error("Acceso denegado.")
    st.stop()

# --- CARGA DE DATOS ---
df_clientes = conn.read(worksheet="clientes", ttl=0)
if 'estado' not in df_clientes.columns: df_clientes['estado'] = 'Activo'

# 3. INTERFAZ SUPERIOR
st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>L E X S C O U T</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; font-size: 14px;'>Sistema de Inteligencia Jurídica Privada</p>", unsafe_allow_html=True)

col_principal, col_derecha = st.columns([3, 1], gap="large")

with col_derecha:
    st.markdown("### 📁 Archivo")
    vista = st.radio("Mostrar:", ["Activos", "Archivados"], horizontal=True)
    df_filtrado = df_clientes[df_clientes['estado'].fillna('Activo') == ('Activo' if vista == "Activos" else 'Archivado')]
    
    for idx, row in df_filtrado.iterrows():
        if st.button(f"💼 {row['nombre_cliente']}", key=f"btn_{idx}", use_container_width=True):
            st.session_state['cliente_sel'] = row['nombre_cliente']
    
    st.divider()
    
    if vista == "Activos" and 'vencimiento' in df_clientes.columns:
        st.markdown("### 📅 Agenda de Vencimientos")
        hoy = datetime.now()
        for _, row in df_filtrado.iterrows():
            if pd.notna(row['vencimiento']):
                try:
                    venc = datetime.strptime(str(row['vencimiento']), "%d/%m/%Y")
                    dias = (venc - hoy).days
                    if 0 <= dias <= 7:
                        st.error(f"**Vence en {dias} días:** {row['nombre_cliente']}")
                except: pass

with col_principal:
    if 'cliente_sel' in st.session_state:
        cliente_actual = st.session_state['cliente_sel']
        datos_c = df_clientes[df_clientes['nombre_cliente'] == cliente_actual].iloc[0]
        
        st.markdown(f"## Expediente: {cliente_actual}")
        
        # FICHA TÉCNICA (Resumen y Vencimiento Automático)
        resumen_texto = datos_c['resumen_caso'] if 'resumen_caso' in df_clientes.columns and pd.notna(datos_c['resumen_caso']) else "Pendiente de análisis por IA..."
        venc_texto = datos_c['vencimiento'] if 'vencimiento' in df_clientes.columns and pd.notna(datos_c['vencimiento']) else "No detectado"
        
        st.markdown(f"""
            <div class="resumen-card">
                <h4 style='margin-top:0; color:#1e3a8a;'>Sinopsis de Estrategia</h4>
                <p style='color: #334155; line-height: 1.6;'>{resumen_texto}</p>
                <hr style='border: 0.5px solid #eee;'>
                <p style='font-size: 13px; color: #1e3a8a;'><b>Próximo Vencimiento Detectado:</b> {venc_texto}</p>
            </div>
        """, unsafe_allow_html=True)
        
        link_nb = datos_c['Link Notebooklm'] if 'Link Notebooklm' in df_clientes.columns else None
        if pd.notna(link_nb):
            st.link_button("🔗 Ir al Libro de NotebookLM", link_nb, use_container_width=True)
        
        st.divider()
        
        # MOTOR DE IA (EXTRACCIÓN AUTOMÁTICA)
        st.markdown("### 📤 Cargar Pieza Procesal para Sincronización")
        st.caption("Al subir el archivo, la IA actualizará automáticamente el resumen y vencimiento del expediente.")
        
        archivo = st.file_uploader("", type="pdf")
        if archivo and "OPENAI_API_KEY" in st.secrets:
            with st.spinner("IA procesando y extrayendo fechas clave..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(archivo.getvalue()); tmp_path = tmp.name
                
                loader = PyPDFLoader(tmp_path)
                docs = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200).split_documents(loader.load())
                
                llm = ChatOpenAI(model="gpt-4o-mini", api_key=st.secrets["OPENAI_API_KEY"])
                
                # INSTRUCCIÓN DE EXTRACCIÓN
                prompt_extraccion = ChatPromptTemplate.from_template(
                    "Eres un experto legal. Analiza el siguiente texto de un expediente y extrae:\n"
                    "1. Un resumen ejecutivo de 3 líneas.\n"
                    "2. La fecha de vencimiento más próxima (en formato DD/MM/AAAA). Si no hay, pon 'Sin fecha'.\n"
                    "Responde SOLO en formato JSON con las llaves 'resumen' y 'vencimiento'.\n\nContexto: {context}"
                )
                
                chain_ia = prompt_extraccion | llm | JsonOutputParser()
                resultado = chain_ia.invoke({"context": docs[0].page_content})
                
                # ACTUALIZAR GOOGLE SHEETS AUTOMÁTICAMENTE
                df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'resumen_caso'] = resultado['resumen']
                if resultado['vencimiento'] != 'Sin fecha':
                    df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'vencimiento'] = resultado['vencimiento']
                
                conn.update(worksheet="clientes", data=df_clientes)
                
                st.success("✅ Expediente actualizado con éxito en la base de datos.")
                st.info(f"**Resumen extraído:** {resultado['resumen']}")
                st.rerun()
                os.remove(tmp_path)
    else:
        st.markdown("<div style='text-align:center; padding:100px; color:#94a3b8;'><h3>Estudio Jurídico Activo</h3><p>Seleccione un expediente de la derecha para trabajar.</p></div>", unsafe_allow_html=True)

# 4. BARRA LATERAL (GESTIÓN)
with st.sidebar:
    st.markdown("### ⚙️ Panel Administrativo")
    with st.expander("➕ Crear Nuevo Expediente"):
        n = st.text_input("Nombre del Cliente")
        l = st.text_input("Link NotebookLM")
        if st.button("Registrar"):
            nueva_fila = pd.DataFrame([{"nombre_cliente": n, "Link Notebooklm": l, "estado": "Activo"}])
            df_upd = pd.concat([df_clientes, nueva_fila], ignore_index=True)
            conn.update(worksheet="clientes", data=df_upd)
            st.success("Creado"); st.rerun()

    if 'cliente_sel' in st.session_state:
        st.divider()
        if st.button("📦 Archivar este caso", use_container_width=True):
            df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'estado'] = 'Archivado'
            conn.update(worksheet="clientes", data=df_clientes)
            st.rerun()
        
        with st.expander("🚨 ELIMINACIÓN"):
            if st.button("Borrar definitivamente", type="primary", use_container_width=True):
                df_final = df_clientes[df_clientes['nombre_cliente'] != cliente_actual]
                conn.update(worksheet="clientes", data=df_final)
                del st.session_state['cliente_sel']; st.rerun()

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import tempfile
from datetime import datetime

# 1. CONFIGURACIÓN Y OCULTAMIENTO DE INTERFAZ
st.set_page_config(page_title="LexScout", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    /* Ocultar elementos de desarrollo de Streamlit */
    header, footer, #MainMenu {visibility: hidden !important;}
    .stDeployButton {display:none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}
    
    /* Fondo Profesional Gris Hueso */
    .stApp {
        background-color: #f4f4f2;
    }
    
    /* Tipografías y Títulos */
    h1, h2, h3 { 
        color: #0c1b33 !important; 
        font-family: 'Georgia', serif;
        font-weight: 800;
    }

    /* Barra Lateral Estilo Bufete (Azul Medianoche) */
    [data-testid="stSidebar"] {
        background-color: #0c1b33;
        border-right: 4px solid #b38b4d; /* Borde Oro */
    }
    [data-testid="stSidebar"] * { color: #ffffff !important; }

    /* BOTONES RESALTADOS (Estilo Ficha) */
    div.stButton > button {
        background-color: #ffffff;
        color: #0c1b33;
        border: 2px solid #b38b4d;
        border-radius: 6px;
        font-weight: bold;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background-color: #b38b4d;
        color: white;
        transform: translateY(-2px);
        box-shadow: 4px 4px 10px rgba(0,0,0,0.2);
    }

    /* Tarjeta de Expediente Seleccionado */
    .resumen-card {
        background-color: #ffffff;
        padding: 30px;
        border-radius: 10px;
        border-top: 10px solid #b38b4d;
        box-shadow: 0 15px 35px rgba(0,0,0,0.1);
        margin-bottom: 30px;
    }
    </style>
    """, unsafe_allow_html=True)

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import JsonOutputParser

# --- CONEXIÓN ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de sistema: {e}"); st.stop()

# 2. LOGIN SEGURO
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center; margin-top: 100px;'>L E X S C O U T</h1>", unsafe_allow_html=True)
    df_socios = conn.read(worksheet="usuarios", ttl=0)
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        u = st.text_input("Credencial"); c = st.text_input("Contraseña", type="password")
        if st.button("Ingresar al Estudio", use_container_width=True):
            if not df_socios[(df_socios['usuario'] == u) & (df_socios['clave'] == c)].empty:
                st.session_state['autenticado'] = True; st.session_state['usuario_actual'] = u; st.rerun()
            else: st.error("Acceso denegado.")
    st.stop()

# --- CARGA DE DATOS ---
df_clientes = conn.read(worksheet="clientes", ttl=0)
if 'estado' not in df_clientes.columns: df_clientes['estado'] = 'Activo'

# 3. INTERFAZ SUPERIOR
st.markdown("<h1 style='text-align: center; letter-spacing: 4px;'>LEXSCOUT</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #555; font-size: 13px; margin-top: -15px;'>Consultoría Jurídica de Inteligencia Avanzada</p>", unsafe_allow_html=True)

col_principal, col_derecha = st.columns([2.5, 1], gap="large")

with col_derecha:
    st.markdown("### 📄 Archivo")
    vista = st.radio("Mostrar:", ["Activos", "Archivados"], horizontal=True)
    df_filtrado = df_clientes[df_clientes['estado'].fillna('Activo') == ('Activo' if vista == "Activos" else 'Archivado')]
    
    st.markdown("---")
    for idx, row in df_filtrado.iterrows():
        # Botones con icono y nombre resaltado
        if st.button(f"💼 {row['nombre_cliente']}", key=f"btn_{idx}", use_container_width=True):
            st.session_state['cliente_sel'] = row['nombre_cliente']
    
    st.divider()
    if vista == "Activos" and 'vencimiento' in df_clientes.columns:
        st.markdown("### ⏳ Próximos Vencimientos")
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
        
        # FICHA DEL CASO (Resumen y Vencimiento Automático)
        resumen_texto = datos_c['resumen_caso'] if 'resumen_caso' in df_clientes.columns and pd.notna(datos_c['resumen_caso']) else "Pendiente de procesamiento por IA..."
        venc_texto = datos_c['vencimiento'] if 'vencimiento' in df_clientes.columns and pd.notna(datos_c['vencimiento']) else "No detectado todavía."
        
        st.markdown(f"""
            <div class="resumen-card">
                <h4 style='margin-top:0; color:#0c1b33;'>Sinopsis Estratégica</h4>
                <p style='color: #444; line-height: 1.7;'>{resumen_texto}</p>
                <hr style='border: 0.5px solid #ddd; margin: 20px 0;'>
                <p style='font-size: 14px; color: #b38b4d;'><b>CALENDARIO JURÍDICO:</b> Próximo vencimiento estimado para el <b>{v_texto if (v_texto := venc_texto) else 'Sin fecha'}</b></p>
            </div>
        """, unsafe_allow_html=True)
        
        link_nb = datos_c['Link Notebooklm'] if 'Link Notebooklm' in df_clientes.columns else None
        if pd.notna(link_nb):
            st.link_button("📜 Acceder al Libro Profundo en NotebookLM", link_nb, use_container_width=True)
        
        st.divider()
        
        # SINCRONIZACIÓN INTELIGENTE
        st.markdown("### 📥 Sincronizar Documentación Nueva")
        st.caption("Suba un PDF para actualizar automáticamente el resumen y los vencimientos en la base de datos.")
        
        archivo = st.file_uploader("", type="pdf", label_visibility="collapsed")
        if archivo and "OPENAI_API_KEY" in st.secrets:
            with st.spinner("IA analizando pieza procesal..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(archivo.getvalue()); tmp_path = tmp.name
                
                loader = PyPDFLoader(tmp_path)
                docs = loader.load()
                
                llm = ChatOpenAI(model="gpt-4o-mini", api_key=st.secrets["OPENAI_API_KEY"])
                prompt_ia = ChatPromptTemplate.from_template(
                    "Eres un secretario judicial experto. Analiza este documento y extrae:\n"
                    "1. Resumen ejecutivo del estado del caso (máximo 4 líneas).\n"
                    "2. La fecha de vencimiento más próxima mencionada (formato DD/MM/AAAA). Si no hay, pon 'Sin fecha'.\n"
                    "Responde SOLO en JSON con llaves 'resumen' y 'vencimiento'.\n\nTexto: {context}"
                )
                
                chain = prompt_ia | llm | JsonOutputParser()
                res = chain.invoke({"context": docs[0].page_content[:4000]})
                
                # ACTUALIZACIÓN EN GOOGLE SHEETS
                df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'resumen_caso'] = res['resumen']
                if res['vencimiento'] != 'Sin fecha':
                    df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'vencimiento'] = res['vencimiento']
                
                conn.update(worksheet="clientes", data=df_clientes)
                st.success("✅ Expediente sincronizado y base de datos actualizada.")
                st.rerun()
                os.remove(tmp_path)
    else:
        st.markdown("<div style='text-align:center; padding-top:150px; color:#aaa;'><h3>Bufete Digital LexScout</h3><p>Seleccione un expediente del archivo lateral para comenzar a operar.</p></div>", unsafe_allow_html=True)

# 4. PANEL DE ADMINISTRACIÓN
with st.sidebar:
    st.markdown("### ⚙️ Administración")
    with st.expander("➕ Alta de Nuevo Expediente"):
        n = st.text_input("Nombre del Cliente")
        l = st.text_input("Link de NotebookLM")
        if st.button("Registrar en Sistema"):
            if n:
                nueva_f = pd.DataFrame([{"nombre_cliente": n, "Link Notebooklm": l, "estado": "Activo"}])
                df_upd = pd.concat([df_clientes, nueva_f], ignore_index=True)
                conn.update(worksheet="clientes", data=df_upd)
                st.success("Registrado"); st.rerun()

    if 'cliente_sel' in st.session_state:
        st.divider()
        if st.button("📦 Archivar este expediente", use_container_width=True):
            df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'estado'] = 'Archivado'
            conn.update(worksheet="clientes", data=df_clientes)
            st.rerun()
        
        with st.expander("🚨 ELIMINACIÓN"):
            if st.button("Borrar definitivamente", type="primary", use_container_width=True):
                df_f = df_clientes[df_clientes['nombre_cliente'] != cliente_actual]
                conn.update(worksheet="clientes", data=df_f)
                del st.session_state['cliente_sel']; st.rerun()

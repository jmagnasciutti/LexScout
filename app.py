import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import tempfile
from datetime import datetime

# 1. CONFIGURACIÓN E INYECCIÓN DE ESTILO (CSS)
st.set_page_config(page_title="LexScout", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    /* Estilo General: Azul Marino y Blanco */
    .main { background-color: #f4f7f9; }
    
    /* Títulos con Serif para mayor formalidad */
    h1, h2, h3 { 
        color: #1e3a8a !important; 
        font-family: 'Playfair Display', serif; 
        font-weight: 700;
    }

    /* Barra lateral corporativa */
    [data-testid="stSidebar"] {
        background-color: #1e3a8a;
        border-right: 2px solid #d4af37;
    }
    [data-testid="stSidebar"] * { color: white !important; }

    /* Botones de la lista derecha (Estilo Fichas) */
    div.stButton > button {
        border: 1px solid #1e3a8a;
        color: #1e3a8a;
        background-color: white;
        border-radius: 5px;
        font-weight: 600;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color: #1e3a8a;
        color: white;
        border: 1px solid #d4af37;
    }

    /* Tarjeta de Resumen (Cuerpo Principal) */
    .resumen-card {
        background-color: white;
        padding: 25px;
        border-radius: 12px;
        border-left: 6px solid #d4af37;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        margin-bottom: 25px;
    }
    </style>
    """, unsafe_allow_html=True)

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# --- CONEXIÓN ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de conexión: {e}"); st.stop()

# 2. LOGIN (Tu lógica original intacta)
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center;'>⚖️ Acceso LexScout</h1>", unsafe_allow_html=True)
    df_socios = conn.read(worksheet="usuarios", ttl=0)
    u = st.text_input("Usuario"); c = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if not df_socios[(df_socios['usuario'] == u) & (df_socios['clave'] == c)].empty:
            st.session_state['autenticado'] = True; st.session_state['usuario_actual'] = u; st.rerun()
        else: st.error("Credenciales incorrectas.")
    st.stop()

# --- CARGA DE DATOS ---
df_clientes = conn.read(worksheet="clientes", ttl=0)
if 'estado' not in df_clientes.columns: df_clientes['estado'] = 'Activo'

# 3. INTERFAZ PROFESIONAL
st.markdown("<h1 style='text-align: center; letter-spacing: 5px; margin-bottom: 0;'>L E X S C O U T</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; font-style: italic;'>Gestión Jurídica & Inteligencia Artificial</p>", unsafe_allow_html=True)
st.divider()

col_principal, col_derecha = st.columns([3, 1], gap="large")

with col_derecha:
    st.markdown("### 📁 Archivo de Casos")
    vista = st.radio("Filtro:", ["Activos", "Archivados"], horizontal=True)
    estado_buscado = 'Activo' if vista == "Activos" else 'Archivado'
    
    # Listado directo de nombres (Botones)
    df_filtrado = df_clientes[df_clientes['estado'].fillna('Activo') == estado_buscado]
    if not df_filtrado.empty:
        for idx, row in df_filtrado.iterrows():
            if st.button(f"📄 {row['nombre_cliente']}", key=f"btn_{idx}", use_container_width=True):
                st.session_state['cliente_sel'] = row['nombre_cliente']
    else:
        st.write("No hay expedientes en esta lista.")
    
    st.divider()
    
    # Alertas de Vencimiento
    if vista == "Activos" and 'vencimiento' in df_clientes.columns:
        st.markdown("### 📅 Alertas Próximas")
        hoy = datetime.now()
        alertas_cont = 0
        for _, row in df_filtrado.iterrows():
            if pd.notna(row['vencimiento']):
                try:
                    venc = datetime.strptime(str(row['vencimiento']), "%d/%m/%Y")
                    dias = (venc - hoy).days
                    if 0 <= dias <= 7:
                        st.error(f"**{row['nombre_cliente']}**\nVence en {dias} días.")
                        alertas_cont += 1
                except: pass
        if alertas_cont == 0: st.success("Sin vencimientos próximos.")

with col_principal:
    if 'cliente_sel' in st.session_state:
        cliente_actual = st.session_state['cliente_sel']
        datos_c = df_clientes[df_clientes['nombre_cliente'] == cliente_actual].iloc[0]
        
        st.markdown(f"## Expediente: {cliente_actual}")
        
        # Resumen Estilo "Ficha Técnica"
        resumen_texto = datos_c['resumen_caso'] if 'resumen_caso' in df_clientes.columns and pd.notna(datos_c['resumen_caso']) else "No se ha cargado un resumen para este caso todavía."
        st.markdown(f"""
            <div class="resumen-card">
                <h4 style='margin-top:0; color:#1e3a8a;'>Resumen del Expediente</h4>
                <p style='color: #334155; line-height: 1.6;'>{resumen_texto}</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Acción: NotebookLM
        link_nb = datos_c['Link Notebooklm'] if 'Link Notebooklm' in df_clientes.columns else None
        if pd.notna(link_nb) and str(link_nb).startswith("http"):
            st.link_button(f"🧠 Abrir NotebookLM de este caso", link_nb, use_container_width=True)
        
        st.divider()
        
        # --- MOTOR DE IA (TU LÓGICA DE SIEMPRE) ---
        st.markdown("### 🔍 Análisis de Documentación Nueva")
        archivo = st.file_uploader("Subir PDF para consulta inmediata", type="pdf")
        if archivo and "OPENAI_API_KEY" in st.secrets:
            with st.spinner("Analizando documento..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(archivo.getvalue()); tmp_path = tmp.name
                
                loader = PyPDFLoader(tmp_path)
                docs = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100).split_documents(loader.load())
                vectorstore = FAISS.from_documents(docs, OpenAIEmbeddings(openai_api_key=st.secrets["OPENAI_API_KEY"]))
                
                model = ChatOpenAI(model="gpt-4o-mini", api_key=st.secrets["OPENAI_API_KEY"])
                prompt = ChatPromptTemplate.from_template("Responde como abogado experto usando solo este contexto: {context}\nPregunta: {question}")
                
                chain = (
                    {"context": vectorstore.as_retriever() | (lambda ds: "\n\n".join(d.page_content for d in ds)), 
                     "question": RunnablePassthrough()}
                    | prompt | model | StrOutputParser()
                )
                
                st.success("✅ Documento analizado. Ya podés preguntar.")
                pregunta = st.text_input("¿Qué necesitás saber de este archivo?")
                if pregunta:
                    st.info(chain.invoke(pregunta))
                os.remove(tmp_path)
    else:
        st.markdown("""
            <div style='text-align:center; margin-top:100px; color:#64748b;'>
                <h3>Bienvenido al Panel de Control</h3>
                <p>Por favor, seleccione un expediente del archivo a su derecha para comenzar.</p>
            </div>
        """, unsafe_allow_html=True)

# 4. BARRA LATERAL ADMINISTRATIVA
with st.sidebar:
    st.markdown("### ⚙️ Administración")
    
    # Alta de casos
    with st.expander("➕ Nuevo Expediente"):
        n = st.text_input("Nombre del Cliente")
        l = st.text_input("Link NotebookLM")
        v = st.text_input("Vencimiento (DD/MM/AAAA)")
        if st.button("Registrar Expediente"):
            if n:
                nueva_fila = pd.DataFrame([{"nombre_cliente": n, "Link Notebooklm": l, "vencimiento": v, "estado": "Activo"}])
                df_upd = pd.concat([df_clientes, nueva_fila], ignore_index=True)
                conn.update(worksheet="clientes", data=df_upd)
                st.success("Expediente creado"); st.rerun()
            else: st.warning("El nombre es obligatorio.")

    # Gestión de Estado y Borrado
    if 'cliente_sel' in st.session_state:
        st.divider()
        st.markdown("### 🗑️ Gestión de Caso")
        
        # Archivar/Desarchivar
        if datos_c['estado'] == 'Activo':
            if st.button("📦 Archivar Caso", use_container_width=True):
                df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'estado'] = 'Archivado'
                conn.update(worksheet="clientes", data=df_clientes)
                st.rerun()
        else:
            if st.button("📤 Devolver a Activos", use_container_width=True):
                df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'estado'] = 'Activo'
                conn.update(worksheet="clientes", data=df_clientes)
                st.rerun()

        # Borrado Definitivo con Doble Seguridad
        with st.expander("🚨 ELIMINAR TOTALMENTE"):
            st.warning("Esta acción eliminará el registro del Sheet.")
            confirmar = st.checkbox("Confirmo eliminación")
            if st.button("ELIMINAR AHORA", type="primary", disabled=not confirmar, use_container_width=True):
                df_final = df_clientes[df_clientes['nombre_cliente'] != cliente_actual]
                conn.update(worksheet="clientes", data=df_final)
                del st.session_state['cliente_sel']
                st.rerun()

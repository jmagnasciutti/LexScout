import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import tempfile
from datetime import datetime

# IMPORTES DE IA
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# 1. CONFIGURACIÓN
st.set_page_config(page_title="LexScout", page_icon="⚖️", layout="wide")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# 2. LOGIN
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
if not st.session_state['autenticado']:
    st.title("⚖️ Acceso LexScout")
    try:
        df_socios = conn.read(worksheet="usuarios", ttl=0)
        u = st.text_input("Usuario")
        c = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            match = df_socios[(df_socios['usuario'] == u) & (df_socios['clave'] == c)]
            if not match.empty:
                st.session_state['autenticado'], st.session_state['usuario_actual'] = True, u
                st.rerun()
            else: st.error("Credenciales incorrectas.")
    except Exception as e: st.error(f"Error: {e}"); st.stop()
    st.stop()

# --- CARGA DE DATOS ---
df_clientes = conn.read(worksheet="clientes", ttl=0)

# 3. INTERFAZ REORGANIZADA
st.title("⚖️ LexScout") # Título limpio como pediste

# CREAMOS COLUMNAS: Cuerpo principal (izquierda) y Listado (derecha)
col_principal, col_derecha = st.columns([3, 1], gap="large")

with col_derecha:
    st.subheader("📁 Expedientes")
    # Listado a simple vista sin selectbox
    for idx, row in df_clientes.iterrows():
        if st.button(row['nombre_cliente'], key=f"btn_{idx}", use_container_width=True):
            st.session_state['cliente_sel'] = row['nombre_cliente']
    
    st.divider()
    # Alerta de Vencimientos
    st.subheader("📅 Alertas")
    if 'vencimiento' in df_clientes.columns:
        hoy = datetime.now()
        for _, row in df_clientes.iterrows():
            if pd.notna(row['vencimiento']):
                venc = datetime.strptime(str(row['vencimiento']), "%d/%m/%Y")
                dias_restantes = (venc - hoy).days
                if 0 <= dias_restantes <= 5:
                    st.error(f"🔥 ¡VENCE EN {dias_restantes} DÍAS!: {row['nombre_cliente']}")
                elif dias_restantes < 0:
                    st.warning(f"🚫 VENCIDO: {row['nombre_cliente']}")

with col_principal:
    if 'cliente_sel' in st.session_state:
        cliente_actual = st.session_state['cliente_sel']
        st.header(f"Caso: {cliente_actual}")
        
        # Datos del cliente seleccionado
        datos_c = df_clientes[df_clientes['nombre_cliente'] == cliente_actual].iloc[0]
        
        # Resumen del Caso
        with st.expander("📝 Ver Resumen del Expediente", expanded=True):
            resumen = datos_c['resumen_caso'] if 'resumen_caso' in df_clientes.columns and pd.notna(datos_c['resumen_caso']) else "Sin resumen cargado."
            st.write(resumen)
        
        # Botón NotebookLM
        link_nb = datos_c['Link Notebooklm'] if 'Link Notebooklm' in df_clientes.columns else None
        if pd.notna(link_nb):
            st.link_button(f"🧠 Ir al Libro de NotebookLM", link_nb)
        
        st.divider()
        
        # Motor de IA Local
        archivo = st.file_uploader("Analizar nuevo PDF para este caso", type="pdf")
        if archivo and "OPENAI_API_KEY" in st.secrets:
            with st.spinner("IA analizando..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(archivo.getvalue()); tmp_path = tmp.name
                
                loader = PyPDFLoader(tmp_path)
                docs = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100).split_documents(loader.load())
                vectorstore = FAISS.from_documents(docs, OpenAIEmbeddings(openai_api_key=st.secrets["OPENAI_API_KEY"]))
                
                model = ChatOpenAI(model="gpt-4o-mini", api_key=st.secrets["OPENAI_API_KEY"])
                prompt = ChatPromptTemplate.from_template("Analiza como abogado: {context}\nPregunta: {question}")
                chain = ({"context": vectorstore.as_retriever() | (lambda ds: "\n\n".join(d.page_content for d in ds)), "question": RunnablePassthrough()} | prompt | model | StrOutputParser())
                
                st.success("✅ PDF procesado.")
                pregunta = st.text_input("Consulta jurídica sobre el archivo:")
                if pregunta:
                    st.info(chain.invoke(pregunta))
                os.remove(tmp_path)
    else:
        st.info("👈 Seleccioná un expediente del listado de la derecha para comenzar.")

# BARRA LATERAL: Solo para administración
with st.sidebar:
    st.header("⚙️ Administración")
    with st.expander("➕ Nuevo Expediente"):
        n = st.text_input("Nombre")
        l = st.text_input("Link Notebook")
        v = st.text_input("Vencimiento (DD/MM/AAAA)")
        if st.button("Crear"):
            # Lógica de guardado (concatenar y conn.update)
            nueva_fila = pd.DataFrame([{"nombre_cliente": n, "Link Notebooklm": l, "vencimiento": v}])
            df_upd = pd.concat([df_clientes, nueva_fila], ignore_index=True)
            conn.update(worksheet="clientes", data=df_upd)
            st.rerun()

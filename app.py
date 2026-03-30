import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import tempfile

# Importes de IA actualizados para máxima compatibilidad
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain.chains.retrieval_qa.base import RetrievalQA
# 1. CONFIGURACIÓN
st.set_page_config(page_title="LexScout: IA Legal", page_icon="⚖️")

# Intentar conectar con la base de datos
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error crítico de configuración: {e}")
    st.stop()

# Funciones de base de datos
def leer_socios(): return conn.read(worksheet="usuarios", ttl=0)
def leer_clientes(): return conn.read(worksheet="clientes", ttl=0)

# 2. LOGIN
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
if not st.session_state['autenticado']:
    st.title("⚖️ Acceso LexScout")
    try:
        df_socios = leer_socios()
        u = st.text_input("Usuario")
        c = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            match = df_socios[(df_socios['usuario'] == u) & (df_socios['clave'] == c)]
            if not match.empty:
                st.session_state['autenticado'], st.session_state['usuario_actual'] = True, u
                st.rerun()
            else: st.error("Credenciales incorrectas.")
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        st.info("Revisá que el link de la planilla esté en los Secrets como 'spreadsheet'.")
    st.stop()

# 3. INTERFAZ Y MOTOR DE IA
st.title(f"⚖️ LexScout: Inteligencia Artificial")
df_clientes = leer_clientes()
cliente_sel = st.selectbox("Seleccionar Expediente", df_clientes['nombre_cliente'].tolist() if not df_clientes.empty else ["Sin clientes"])

archivo = st.file_uploader("Subir PDF", type="pdf")
if archivo and "OPENAI_API_KEY" in st.secrets:
    with st.spinner("Analizando..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(archivo.getvalue()); tmp_path = tmp.name
        
        loader = PyPDFLoader(tmp_path)
        docs = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100).split_documents(loader.load())
        vectorstore = FAISS.from_documents(docs, OpenAIEmbeddings(openai_api_key=st.secrets["OPENAI_API_KEY"]))
        
        llm = ChatOpenAI(model="gpt-4o-mini", api_key=st.secrets["OPENAI_API_KEY"])
        qa_chain = RetrievalQA.from_chain_type(llm, chain_type="stuff", retriever=vectorstore.as_retriever())
        
        st.success("✅ Listo para preguntar.")
        pregunta = st.text_input("¿Qué necesitás saber?")
        if pregunta:
            res = qa_chain.invoke(pregunta)
            st.info(res["result"])
        os.remove(tmp_path)

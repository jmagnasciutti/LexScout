import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import tempfile

# IMPORTES 2026 (Rutas directas para evitar errores de módulos)
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate

# 1. CONFIGURACIÓN
st.set_page_config(page_title="LexScout: IA Legal", page_icon="⚖️")

# Conexión ultra-segura
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de configuración en Secrets: {e}")
    st.stop()

# 2. LOGIN
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.title("⚖️ Acceso LexScout")
    try:
        # Aquí es donde fallaba: le decimos que espere a la planilla
        df_socios = conn.read(worksheet="usuarios", ttl=0)
        u = st.text_input("Usuario")
        c = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            match = df_socios[(df_socios['usuario'] == u) & (df_socios['clave'] == c)]
            if not match.empty:
                st.session_state['autenticado'], st.session_state['usuario_actual'] = True, u
                st.rerun()
            else: st.error("Credenciales incorrectas.")
    except Exception as e:
        st.error(f"Error: No encuentro la pestaña 'usuarios' en tu Google Sheet.")
        st.info("Revisá que el nombre de la pestaña abajo en el Excel sea 'usuarios'.")
    st.stop()

# 3. INTERFAZ Y MOTOR DE IA
st.title(f"⚖️ LexScout: Inteligencia Artificial")
try:
    df_clientes = conn.read(worksheet="clientes", ttl=0)
    cliente_sel = st.selectbox("Expediente", df_clientes['nombre_cliente'].tolist())
except:
    st.warning("No se pudo cargar la lista de clientes. Creá la pestaña 'clientes' en tu Sheet.")
    cliente_sel = "General"

archivo = st.file_uploader("Subir PDF del caso", type="pdf")

if archivo and "OPENAI_API_KEY" in st.secrets:
    with st.spinner("Analizando..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(archivo.getvalue()); tmp_path = tmp.name
        
        loader = PyPDFLoader(tmp_path)
        docs = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100).split_documents(loader.load())
        vectorstore = FAISS.from_documents(docs, OpenAIEmbeddings(openai_api_key=st.secrets["OPENAI_API_KEY"]))
        
        llm = ChatOpenAI(model="gpt-4o-mini", api_key=st.secrets["OPENAI_API_KEY"])
        prompt = ChatPromptTemplate.from_template("Responde como abogado basándote solo en esto: {context}\nPregunta: {input}")
        
        # Sistema moderno de cadenas
        combine_docs_chain = create_stuff_documents_chain(llm, prompt)
        retrieval_chain = create_retrieval_chain(vectorstore.as_retriever(), combine_docs_chain)
        
        st.success("✅ Documento listo.")
        pregunta = st.text_input("¿Qué necesitás saber?")
        if pregunta:
            res = retrieval_chain.invoke({"input": pregunta})
            st.info(res["answer"])
        os.remove(tmp_path)

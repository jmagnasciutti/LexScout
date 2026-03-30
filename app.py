import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import tempfile

# IMPORTES MODERNOS DE IA
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# 1. CONFIGURACIÓN
st.set_page_config(page_title="LexScout: IA Legal", page_icon="⚖️")
conn = st.connection("gsheets", type=GSheetsConnection)

# Funciones de base de datos
def leer_socios(): return conn.read(worksheet="usuarios", ttl=0)
def leer_clientes(): return conn.read(worksheet="clientes", ttl=0)
def guardar_cliente_db(nombre):
    df_actual = leer_clientes()
    nuevo_df = pd.concat([df_actual, pd.DataFrame([{"nombre_cliente": nombre}])], ignore_index=True)
    conn.update(worksheet="clientes", data=nuevo_df)

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
    except Exception as e: st.error(f"Error de conexión: {e}")
    st.stop()

# 3. INTERFAZ
st.title(f"⚖️ LexScout: Inteligencia Artificial")
with st.sidebar:
    st.header("📂 Expedientes")
    nuevo_c = st.text_input("Nuevo Cliente")
    if st.button("Crear"):
        if nuevo_c: guardar_cliente_db(nuevo_c); st.rerun()
    st.divider()
    df_clientes = leer_clientes()
    cliente_sel = st.selectbox("Seleccionar Expediente", df_clientes['nombre_cliente'].tolist())

# 4. MOTOR DE IA
archivo = st.file_uploader("Subir PDF del caso", type="pdf")
if archivo:
    with st.spinner("Analizando..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(archivo.getvalue()); tmp_path = tmp.name
        
        loader = PyPDFLoader(tmp_path)
        docs = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100).split_documents(loader.load())
        vectorstore = FAISS.from_documents(docs, OpenAIEmbeddings(openai_api_key=st.secrets["OPENAI_API_KEY"]))
        
        llm = ChatOpenAI(model="gpt-4o-mini", api_key=st.secrets["OPENAI_API_KEY"])
        prompt = ChatPromptTemplate.from_template("Responde la pregunta basándote solo en el contexto: {context}\nPregunta: {input}")
        
        chain = create_retrieval_chain(vectorstore.as_retriever(), create_stuff_documents_chain(llm, prompt))
        st.success("✅ Documento listo.")
        
        pregunta = st.text_input("¿Qué necesitás saber?")
        if pregunta:
            res = chain.invoke({"input": pregunta})
            st.info(res["answer"])
        os.remove(tmp_path)

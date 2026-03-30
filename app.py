import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import tempfile

# IMPORTES MODERNOS (Sin la carpeta 'chains' que falla)
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

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
    clientes_list = df_clientes['nombre_cliente'].tolist() if not df_clientes.empty else []
    cliente_sel = st.selectbox("Seleccionar Expediente", clientes_list)

# 4. MOTOR DE IA (Sintaxis LCEL 2026)
archivo = st.file_uploader("Subir PDF del caso", type="pdf")
if archivo and cliente_sel:
    with st.spinner("Procesando expediente..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(archivo.getvalue()); tmp_path = tmp.name
        
        # Carga y procesado
        loader = PyPDFLoader(tmp_path)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        docs = text_splitter.split_documents(loader.load())
        
        # Memoria y Cerebro
        vectorstore = FAISS.from_documents(docs, OpenAIEmbeddings(openai_api_key=st.secrets["OPENAI_API_KEY"]))
        retriever = vectorstore.as_retriever()
        model = ChatOpenAI(model="gpt-4o-mini", api_key=st.secrets["OPENAI_API_KEY"])
        
        # El "Cerebro" de LexScout (Moderno)
        template = """Responde como un abogado experto basándote solo en este contexto:
        {context}
        Pregunta: {question}"""
        prompt = ChatPromptTemplate.from_template(template)
        
        def format_docs(documents):
            return "\n\n".join(doc.page_content for doc in documents)

        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | model
            | StrOutputParser()
        )

        st.success("✅ Documento analizado.")
        pregunta = st.text_input("¿Qué necesitás saber de este archivo?")
        if pregunta:
            respuesta = rag_chain.invoke(pregunta)
            st.info(respuesta)
        os.remove(tmp_path)

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import tempfile

# IMPORTES MODERNOS (No usamos la carpeta 'chains' para evitar el error)
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# 1. CONFIGURACIÓN
st.set_page_config(page_title="LexScout: IA Legal", page_icon="⚖️")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# 2. LOGIN
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

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
    except Exception as e:
        st.error(f"Error al conectar con la planilla: {e}")
    st.stop()

# 3. MOTOR DE INTELIGENCIA ARTIFICIAL
st.title(f"⚖️ LexScout: Inteligencia Artificial")
df_clientes = conn.read(worksheet="clientes", ttl=0)
cliente_sel = st.selectbox("Seleccionar Expediente", df_clientes['nombre_cliente'].tolist() if not df_clientes.empty else ["Sin clientes"])

archivo = st.file_uploader("Subir PDF del caso", type="pdf")

if archivo and "OPENAI_API_KEY" in st.secrets:
    with st.spinner("Analizando documento..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(archivo.getvalue()); tmp_path = tmp.name
        
        # Procesamiento del PDF
        loader = PyPDFLoader(tmp_path)
        docs = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100).split_documents(loader.load())
        vectorstore = FAISS.from_documents(docs, OpenAIEmbeddings(openai_api_key=st.secrets["OPENAI_API_KEY"]))
        retriever = vectorstore.as_retriever()

        # El nuevo "Cerebro" (Sin usar la carpeta .chains que te da error)
        model = ChatOpenAI(model="gpt-4o-mini", api_key=st.secrets["OPENAI_API_KEY"])
        template = "Responde como abogado experto usando solo este contexto: {context}\nPregunta: {question}"
        prompt = ChatPromptTemplate.from_template(template)

        # La "Tubería" de IA
        chain = (
            {"context": retriever | (lambda docs: "\n\n".join(d.page_content for d in docs)), 
             "question": RunnablePassthrough()}
            | prompt | model | StrOutputParser()
        )

        st.success("✅ Documento procesado con éxito.")
        pregunta = st.text_input("¿Qué necesitás saber de este archivo?")
        if pregunta:
            respuesta = chain.invoke(pregunta)
            st.info(respuesta)
        os.remove(tmp_path)

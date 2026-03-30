import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import tempfile

# Importes de IA actualizados
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
# Esta es la línea que estaba fallando, ahora corregida:
from langchain.chains.retrieval_qa.base import RetrievalQA
# 1. CONFIGURACIÓN E INICIO
st.set_page_config(page_title="LexScout: IA Legal", page_icon="⚖️")

# Conexión a Google Sheets (Base de Datos)
conn = st.connection("gsheets", type=GSheetsConnection)

def leer_socios():
    return conn.read(worksheet="usuarios", ttl=0)

def leer_clientes():
    return conn.read(worksheet="clientes", ttl=0)

def guardar_cliente_db(nombre):
    df_actual = leer_clientes()
    nuevo_df = pd.concat([df_actual, pd.DataFrame([{"nombre_cliente": nombre}])], ignore_index=True)
    conn.update(worksheet="clientes", data=nuevo_df)

# 2. SEGURIDAD DE ACCESO
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.title("⚖️ Acceso al Estudio LexScout")
    try:
        df_socios = leer_socios()
        u = st.text_input("Usuario")
        c = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            match = df_socios[(df_socios['usuario'] == u) & (df_socios['clave'] == c)]
            if not match.empty:
                st.session_state['autenticado'] = True
                st.session_state['usuario_actual'] = u
                st.rerun()
            else:
                st.error("Credenciales incorrectas.")
    except Exception as e:
        st.error(f"Error de base de datos: {e}")
    st.stop()

# 3. INTERFAZ PRINCIPAL
st.title("⚖️ LexScout: Inteligencia Artificial")
st.write(f"Sesión activa: **Dr./Dra. {st.session_state['usuario_actual'].title()}**")

# Gestión de Clientes
with st.sidebar:
    st.header("📂 Expedientes")
    nuevo_c = st.text_input("Nuevo Cliente")
    if st.button("Crear"):
        if nuevo_c:
            guardar_cliente_db(nuevo_c)
            st.success("Guardado.")
            st.rerun()
    
    st.divider()
    df_clientes = leer_clientes()
    cliente_sel = st.selectbox("Seleccionar Expediente", df_clientes['nombre_cliente'].tolist())

# 4. MOTOR DE INTELIGENCIA ARTIFICIAL
st.subheader(f"Análisis del Expediente: {cliente_sel}")
archivo = st.file_uploader("Subir PDF del caso", type="pdf")

if archivo:
    with st.spinner("Analizando documento..."):
        # Guardar archivo temporalmente para que LangChain lo lea
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(archivo.getvalue())
            tmp_path = tmp.name

        # Procesar PDF
        loader = PyPDFLoader(tmp_path)
        paginas = loader.load()
        
        # Dividir texto en trozos para la IA
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        docs = text_splitter.split_documents(paginas)
        
        # Crear base de conocimientos temporal (FAISS)
        embeddings = OpenAIEmbeddings(openai_api_key=st.secrets["OPENAI_API_KEY"])
        vectorstore = FAISS.from_documents(docs, embeddings)
        
        # Configurar el "Cerebro"
        llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0, openai_api_key=st.secrets["OPENAI_API_KEY"])
        qa_chain = RetrievalQA.from_chain_type(llm, chain_type="stuff", retriever=vectorstore.as_retriever())

        st.success("✅ Documento procesado con éxito.")
        
        # Chat con el Expediente
        pregunta = st.text_input("¿Qué necesitás saber de este documento?")
        if pregunta:
            respuesta = qa_chain.invoke(pregunta)
            st.write("### 🤖 Respuesta de LexScout:")
            st.info(respuesta["result"])
            
        os.remove(tmp_path) # Limpiar archivo temporal

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import tempfile

# IMPORTES MODERNOS: Evitamos 'langchain.chains' para que no falle
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
        st.error(f"Error de base de datos: {e}")
    st.stop()

# 3. INTERFAZ Y MOTOR DE IA
st.title(f"⚖️ LexScout: Inteligencia Artificial")

# Función para guardar nuevo expediente
def guardar_nuevo_expediente(nombre, link):
    try:
        # Leemos los datos actuales
        df_existente = conn.read(worksheet="clientes", ttl=0)
        
        # Creamos la nueva fila (Aseguramos que los nombres de columnas coincidan con tu Excel)
        nueva_fila = pd.DataFrame([{
            "nombre_cliente": nombre,
            "fecha_creación": pd.Timestamp.now().strftime("%d/%m/%Y"),
            "Link Notebooklm": link
        }])
        
        # Unimos y subimos
        df_actualizado = pd.concat([df_existente, nueva_fila], ignore_index=True)
        conn.update(worksheet="clientes", data=df_actualizado)
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

# BARRA LATERAL: Gestión de Expedientes
with st.sidebar:
    st.header("📋 Gestión de Estudio")
    
    # Formulario para nuevos socios
    with st.expander("➕ Crear Nuevo Expediente"):
        nuevo_nombre = st.text_input("Nombre del Caso / Cliente")
        nuevo_link = st.text_input("Link de NotebookLM (opcional)")
        
        if st.button("Registrar en Base de Datos"):
            if nuevo_nombre:
                if guardar_nuevo_expediente(nuevo_nombre, nuevo_link):
                    st.success(f"Expediente '{nuevo_nombre}' creado con éxito.")
                    st.balloons()
                    st.rerun()
            else:
                st.warning("El nombre del expediente es obligatorio.")
    
    st.divider()
    st.info(f"Conectado como: {st.session_state['usuario_actual']}")

# CUERPO PRINCIPAL: Selección y Análisis
try:
    df_clientes = conn.read(worksheet="clientes", ttl=0)
    opciones = df_clientes['nombre_cliente'].tolist() if not df_clientes.empty else ["Sin clientes"]
    cliente_sel = st.selectbox("Seleccionar Expediente Activo", opciones)

    # Botón dinámico de NotebookLM
    nombre_col_link = "Link Notebooklm"
    if nombre_col_link in df_clientes.columns:
        fila = df_clientes[df_clientes['nombre_cliente'] == cliente_sel]
        link_nb = fila[nombre_col_link].values[0] if not fila.empty else None
        
        if pd.notna(link_nb) and str(link_nb).startswith("http"):
            st.link_button(f"🧠 Abrir NotebookLM: {cliente_sel}", link_nb, use_container_width=True)
    
    st.divider()

except Exception as e:
    st.error(f"Error al cargar la lista de expedientes: {e}")

# Motor de análisis de PDF local
archivo = st.file_uploader("Subir PDF nuevo para análisis inmediato", type="pdf")

if archivo and "OPENAI_API_KEY" in st.secrets:
    with st.spinner("Procesando documento legal..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(archivo.getvalue())
            tmp_path = tmp.name
        
        loader = PyPDFLoader(tmp_path)
        docs = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100).split_documents(loader.load())
        vectorstore = FAISS.from_documents(docs, OpenAIEmbeddings(openai_api_key=st.secrets["OPENAI_API_KEY"]))
        retriever = vectorstore.as_retriever()

        template = "Responde como abogado experto usando solo este contexto: {context}\nPregunta: {question}"
        prompt = ChatPromptTemplate.from_template(template)
        model = ChatOpenAI(model="gpt-4o-mini", api_key=st.secrets["OPENAI_API_KEY"])

        chain = (
            {"context": retriever | (lambda documents: "\n\n".join(d.page_content for d in documents)), 
             "question": RunnablePassthrough()}
            | prompt | model | StrOutputParser()
        )

        st.success("✅ Análisis completo.")
        pregunta = st.text_input("¿Qué necesitás consultar de este archivo?")
        if pregunta:
            respuesta = chain.invoke(pregunta)
            st.info(respuesta)
        os.remove(tmp_path)

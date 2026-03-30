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

try:
    df_clientes = conn.read(worksheet="clientes", ttl=0)
    
    # Selector de expediente
    opciones = df_clientes['nombre_cliente'].tolist() if not df_clientes.empty else ["Sin clientes"]
    cliente_sel = st.selectbox("Seleccionar Expediente", opciones)

    # --- AJUSTE DE NOMBRE DE COLUMNA: Debe ser igual al Excel ---
    nombre_columna = "Link Notebooklm" 

    if not df_clientes.empty:
        if nombre_columna in df_clientes.columns:
            # Buscamos el link del cliente elegido
            fila = df_clientes[df_clientes['nombre_cliente'] == cliente_sel]
            link_nb = fila[nombre_columna].values[0] if not fila.empty else None
            
            if pd.notna(link_nb) and str(link_nb).startswith("http"):
                st.link_button(f"🧠 Abrir NotebookLM: {cliente_sel}", link_nb, use_container_width=True)
            else:
                st.warning(f"⚠️ El expediente '{cliente_sel}' no tiene un link cargado en la columna '{nombre_columna}'.")
        else:
            st.error(f"❌ Error: No encontré la columna '{nombre_columna}' en tu Excel.")
            st.info(f"Revisá que en la pestaña 'clientes' el encabezado diga exactamente: {nombre_columna}")
    
    st.divider()

except Exception as e:
    st.error(f"Error al cargar datos: {e}")

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import tempfile
from datetime import datetime

# 1. CONFIGURACIÓN E IMPORTES
st.set_page_config(page_title="LexScout", page_icon="⚖️", layout="wide")
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de conexión: {e}"); st.stop()

# 2. LOGIN (Mantenemos tu lógica actual)
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
if not st.session_state['autenticado']:
    st.title("⚖️ Acceso LexScout")
    df_socios = conn.read(worksheet="usuarios", ttl=0)
    u = st.text_input("Usuario"); c = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if not df_socios[(df_socios['usuario'] == u) & (df_socios['clave'] == c)].empty:
            st.session_state['autenticado'] = True; st.session_state['usuario_actual'] = u; st.rerun()
        else: st.error("Credenciales incorrectas.")
    st.stop()

# --- CARGA DE DATOS ---
df_clientes = conn.read(worksheet="clientes", ttl=0)
if 'estado' not in df_clientes.columns:
    df_clientes['estado'] = 'Activo'

# 3. INTERFAZ
st.title("⚖️ LexScout")

col_principal, col_derecha = st.columns([3, 1], gap="large")

with col_derecha:
    # Selector de vista: Activos o Archivados
    vista = st.radio("Ver expedientes:", ["Activos", "Archivados"], horizontal=True)
    estado_buscado = 'Activo' if vista == "Activos" else 'Archivado'
    
    st.subheader(f"📁 {vista}")
    
    # Filtrar y mostrar lista
    df_filtrado = df_clientes[df_clientes['estado'].fillna('Activo') == estado_buscado]
    for idx, row in df_filtrado.iterrows():
        if st.button(row['nombre_cliente'], key=f"btn_{idx}", use_container_width=True):
            st.session_state['cliente_sel'] = row['nombre_cliente']
    
    st.divider()
    # Alertas (Solo para activos)
    if vista == "Activos" and 'vencimiento' in df_clientes.columns:
        st.subheader("📅 Alertas")
        hoy = datetime.now()
        for _, row in df_filtrado.iterrows():
            if pd.notna(row['vencimiento']):
                try:
                    venc = datetime.strptime(str(row['vencimiento']), "%d/%m/%Y")
                    dias = (venc - hoy).days
                    if 0 <= dias <= 5: st.error(f"🔥 VENCE EN {dias} DÍAS: {row['nombre_cliente']}")
                except: pass

with col_principal:
    if 'cliente_sel' in st.session_state:
        cliente_actual = st.session_state['cliente_sel']
        st.header(f"Caso: {cliente_actual}")
        datos_c = df_clientes[df_clientes['nombre_cliente'] == cliente_actual].iloc[0]
        
        # Resumen y NotebookLM
        with st.expander("📝 Resumen del Expediente", expanded=True):
            st.write(datos_c['resumen_caso'] if 'resumen_caso' in df_clientes.columns and pd.notna(datos_c['resumen_caso']) else "Sin resumen.")
        
        link_nb = datos_c['Link Notebooklm'] if 'Link Notebooklm' in df_clientes.columns else None
        if pd.notna(link_nb): st.link_button(f"🧠 Ir al Libro de NotebookLM", link_nb)
        
        st.divider()
        
        # IA local (Tu motor de siempre)
        archivo = st.file_uploader("Analizar PDF", type="pdf")
        if archivo and "OPENAI_API_KEY" in st.secrets:
            # ... (Aquí va tu bloque de procesamiento de IA que ya tenés) ...
            st.success("Motor de IA operativo para este caso.")
    else:
        st.info("👈 Seleccioná un expediente del listado.")

# 4. BARRA LATERAL: GESTIÓN Y ZONA DE PELIGRO
with st.sidebar:
    st.header("⚙️ Administración")
    
    # Alta de casos
    with st.expander("➕ Nuevo Expediente"):
        n = st.text_input("Nombre")
        l = st.text_input("Link Notebook")
        v = st.text_input("Vencimiento (DD/MM/AAAA)")
        if st.button("Crear"):
            nueva_fila = pd.DataFrame([{"nombre_cliente": n, "Link Notebooklm": l, "vencimiento": v, "estado": "Activo"}])
            df_upd = pd.concat([df_clientes, nueva_fila], ignore_index=True)
            conn.update(worksheet="clientes", data=df_upd)
            st.success("Creado"); st.rerun()

    # --- ZONA DE GESTIÓN DE ESTADO Y BORRADO ---
    if 'cliente_sel' in st.session_state:
        st.divider()
        st.subheader("🗑️ Gestión de Caso")
        
        # Botón para Archivar/Desarchivar
        if datos_c['estado'] == 'Activo':
            if st.button("📦 Archivar Expediente", use_container_width=True):
                df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'estado'] = 'Archivado'
                conn.update(worksheet="clientes", data=df_clientes)
                st.rerun()
        else:
            if st.button("📤 Volver a Activos", use_container_width=True):
                df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'estado'] = 'Activo'
                conn.update(worksheet="clientes", data=df_clientes)
                st.rerun()

        # Botón para Borrar Definitivo
        with st.expander("🚨 ELIMINAR DEFINITIVAMENTE"):
            st.warning("Esta acción no se puede deshacer.")
            confirmar = st.checkbox("Confirmo eliminación total")
            if st.button("BORRAR AHORA", type="primary", disabled=not confirmar, use_container_width=True):
                df_final = df_clientes[df_clientes['nombre_cliente'] != cliente_actual]
                conn.update(worksheet="clientes", data=df_final)
                del st.session_state['cliente_sel']
                st.rerun()

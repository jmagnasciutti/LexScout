import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import os
import json

st.set_page_config(page_title="LexScout", page_icon="⚖️", layout="wide")

# --- CONFIGURACIÓN ---
URL_EXCEL = "https://docs.google.com/spreadsheets/d/1QUO2R_9LHCful9g4OTVqKQDc4Hxs3FmyyxSdsQeWux8"

# --- FUNCIÓN INTELIGENTE DE CONEXIÓN ---
def conectar_estudio():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # 1. Intentamos leer el archivo local (para cuando usas tu PC)
    if os.path.exists("secretos.json"):
        creds = ServiceAccountCredentials.from_json_keyfile_name("secretos.json", scope)
    
    # 2. Si no existe, buscamos en los "Secrets" de la nube
    elif "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    
    else:
        st.error("❌ No se encontró la llave 'secretos.json' ni localmente ni en la nube.")
        st.stop()
        
    client = gspread.authorize(creds)
    return client.open_by_url(URL_EXCEL).worksheet("clientes")

# --- SISTEMA DE LOGIN ---
if "autenticado" not in st.session_state:
    st.markdown("<h2 style='text-align: center;'>🔐 Acceso al Estudio</h2>", unsafe_allow_html=True)
    clave = st.text_input("Ingrese la clave de LexScout:", type="password")
    if st.button("Entrar"):
        if clave == "lex123":
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Clave incorrecta")
else:
    # --- PANEL PRINCIPAL ---
    try:
        sheet = conectar_estudio()
        df = pd.DataFrame(sheet.get_all_records())

        st.title("⚖️ Panel de Gestión LexScout")
        
        # Métricas
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Causas", len(df))
        c2.metric("🔴 Urgentes", df[df['Informe_Vigia'].str.contains("🔴")].shape[0] if 'Informe_Vigia' in df else 0)
        c3.metric("🟡 Novedades", df[df['Informe_Vigia'].str.contains("🟡")].shape[0] if 'Informe_Vigia' in df else 0)

        st.divider()

        # Listado de Causas
        for index, row in df.iterrows():
            with st.container(border=True):
                col_text, col_btns = st.columns([5, 1])
                with col_text:
                    st.subheader(row.get('nombre_cliente', 'Sin Nombre'))
                    with st.expander("📄 Ver Informe"):
                        st.write(row.get('Informe_Vigia', 'Sin informe disponible'))
                with col_btns:
                    if st.button("🗑️ Borrar", key=f"del_{index}"):
                        sheet.delete_rows(index + 2)
                        st.success("Eliminado")
                        st.rerun()
                        
    except Exception as e:
        st.error(f"Error en la conexión: {e}")

if st.sidebar.button("Salir"):
    del st.session_state["autenticado"]
    st.rerun()

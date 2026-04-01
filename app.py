import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import time

st.set_page_config(page_title="LexScout", page_icon="⚖️", layout="wide")

# --- CONFIGURACIÓN ---
GOOGLE_JSON = "secretos.json"
URL_EXCEL = "https://docs.google.com/spreadsheets/d/1QUO2R_9LHCful9g4OTVqKQDc4Hxs3FmyyxSdsQeWux8"

# --- SISTEMA DE LOGIN ---
def login():
    if "autenticado" not in st.session_state:
        st.markdown("<h2 style='text-align: center;'>🔐 Acceso al Estudio</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            clave = st.text_input("Ingrese la clave de LexScout:", type="password")
            if st.button("Entrar"):
                if clave == "lex123": # <--- Tu clave de acceso
                    st.session_state["autenticado"] = True
                    st.rerun()
                else:
                    st.error("❌ Clave incorrecta")
        return False
    return True

if login():
    try:
        # --- CONEXIÓN ---
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(URL_EXCEL).worksheet("clientes")
        
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        st.title("⚖️ Panel de Gestión LexScout")
        
        # --- MÉTRICAS ---
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Causas", len(df))
        c2.metric("🔴 Urgentes", df[df['Informe_Vigia'].str.contains("🔴")].shape[0])
        c3.metric("🟡 Novedades", df[df['Informe_Vigia'].str.contains("🟡")].shape[0])

        st.divider()

        # --- LISTADO DE CAUSAS ---
        for index, row in df.iterrows():
            with st.container(border=True):
                col_text, col_btns = st.columns([4, 1])
                
                with col_text:
                    st.subheader(row['nombre_cliente'])
                    with st.expander("📄 Ver Reporte del Vigía"):
                        st.write(row['Informe_Vigia'])
                
                with col_btns:
                    # Botón de Archivar
                    if st.button("🗄️ Archivar", key=f"arc_{index}"):
                        st.toast(f"Archivando {row['nombre_cliente']}...")
                        # Aquí podrías mover la fila a otra hoja
                    
                    # Botón de Borrar (ELIMINA DE GOOGLE SHEETS)
                    if st.button("🗑️ Borrar", key=f"del_{index}"):
                        sheet.delete_rows(index + 2) # +2 por encabezado y base 1
                        st.success("Causa eliminada del sistema.")
                        time.sleep(1)
                        st.rerun()

        if st.sidebar.button("Cerrar Sesión"):
            del st.session_state["autenticado"]
            st.rerun()

    except Exception as e:
        st.error(f"Error en la conexión con el Excel: {e}")

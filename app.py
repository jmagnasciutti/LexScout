import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

st.set_page_config(page_title="LexScout", page_icon="⚖️", layout="wide")

# --- CONFIGURACIÓN ---
GOOGLE_JSON = "secretos.json"
URL_EXCEL = "TU_URL_DE_EXCEL_AQUÍ" # <--- ¡IMPORTANTE: PEGÁ TU URL ACÁ!

# --- SISTEMA DE LOGIN ---
def login():
    if "autenticado" not in st.session_state:
        st.markdown("<h2 style='text-align: center;'>🔐 Acceso Restringido</h2>", unsafe_allow_html=True)
        clave = st.text_input("Clave del Estudio:", type="password")
        if st.button("Entrar"):
            if clave == "lex123": # <--- Cambiá esta clave a tu gusto
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Clave incorrecta")
        return False
    return True

if login():
    # --- CONEXIÓN A DATOS ---
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(URL_EXCEL).worksheet("clientes")
        
        # Leemos los datos
        records = sheet.get_all_records()
        df = pd.DataFrame(records)

        # --- INTERFAZ ---
        st.title("⚖️ LexScout - Panel de Gestión")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Causas Totales", len(df))
        c2.metric("🔴 Urgentes", df[df['Informe_Vigia'].str.contains("🔴")].shape[0])
        c3.metric("🟡 Novedades", df[df['Informe_Vigia'].str.contains("🟡")].shape[0])
        
        st.divider()

        # --- LISTADO CON BOTONES ---
        for index, row in df.iterrows():
            with st.container(border=True):
                col_texto, col_btn1, col_btn2 = st.columns([6, 1, 1])
                
                with col_texto:
                    st.subheader(row['nombre_cliente'])
                    with st.expander("Ver Informe Completo"):
                        st.write(row['Informe_Vigia'])
                
                with col_btn1:
                    if st.button("🗄️ Archivar", key=f"arc_{index}"):
                        st.info("Función de archivo en desarrollo...")
                
                with col_btn2:
                    if st.button("🗑️ Borrar", key=f"del_{index}"):
                        # Borramos la fila en Google Sheets (index + 2 por el encabezado)
                        sheet.delete_rows(index + 2)
                        st.success(f"Causa {row['nombre_cliente']} eliminada.")
                        time.sleep(1)
                        st.rerun()

        if st.sidebar.button("Cerrar Sesión"):
            del st.session_state["autenticado"]
            st.rerun()

    except Exception as e:
        st.error(f"Error de conexión: {e}")

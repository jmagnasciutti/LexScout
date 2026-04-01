import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="LexScout", page_icon="⚖️", layout="wide")
GOOGLE_JSON = "secretos.json"
URL_EXCEL = "TU_URL_DE_EXCEL_AQUÍ" # <--- PEGÁ TU URL DE EXCEL ACÁ

# --- FUNCIONES DE BASE DE DATOS ---
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON, scope)
    client = gspread.authorize(creds)
    return client.open_by_url(URL_EXCEL).worksheet("clientes")

# --- LOGIN ---
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center;'>🔐 Acceso a LexScout</h2>", unsafe_allow_html=True)
        password = st.text_input("Ingrese la clave del Estudio:", type="password")
        if st.button("Ingresar"):
            if password == "lex123": # <--- CAMBIÁ ESTA CLAVE POR LA QUE QUIERAS
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Clave incorrecta")
        return False
    return True

if check_password():
    sheet = conectar_google_sheets()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    st.title("⚖️ Panel de Control LexScout")

    # --- MÉTRICAS ---
    urgentes = df[df['Informe_Vigia'].str.contains("🔴")].shape[0]
    novedades = df[df['Informe_Vigia'].str.contains("🟡")].shape[0]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Causas", len(df))
    c2.metric("🔴 Urgentes", urgentes)
    c3.metric("🟡 Novedades", novedades)

    st.divider()

    # --- LISTADO DE EXPEDIENTES ---
    st.subheader("📁 Gestión de Expedientes")

    for i, row in df.iterrows():
        # Usamos un contenedor visual para cada causa
        with st.container(border=True):
            col_info, col_btn1, col_btn2 = st.columns([6, 1, 1])
            
            with col_info:
                st.markdown(f"**{row['nombre_cliente']}**")
                with st.expander("Ver Informe del Vigía"):
                    st.write(row['Informe_Vigia'])
            
            with col_btn1:
                if st.button("🗄️ Archivar", key=f"arc_{i}"):
                    # Aquí podrías mover a otra hoja, por ahora solo marcamos
                    st.toast("Causa Archivada (Próximamente funcional)")
            
            with col_btn2:
                if st.button("🗑️ Eliminar", key=f"del_{i}"):
                    sheet.delete_rows(i + 2) # i+2 porque Sheets empieza en 1 y tiene encabezado
                    st.warning(f"Eliminado: {row['nombre_cliente']}")
                    st.rerun()

    if st.sidebar.button("Cerrar Sesión"):
        del st.session_state["password_correct"]
        st.rerun()sar las novedades.")

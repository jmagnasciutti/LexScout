import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os

# 1. CONFIGURACIÓN E INICIO DE CONEXIÓN
st.set_page_config(page_title="LexScout: Despacho Digital", page_icon="⚖️")

# Conectamos con el "Secretario Virtual" de Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Funciones para manejar la base de datos
def leer_socios():
    return conn.read(worksheet="usuarios", ttl=0)

def leer_clientes():
    return conn.read(worksheet="clientes", ttl=0)

def guardar_cliente_db(nombre):
    df_actual = leer_clientes()
    nuevo_dato = pd.DataFrame([{"nombre_cliente": nombre}])
    nuevo_df = pd.concat([df_actual, nuevo_dato], ignore_index=True)
    conn.update(worksheet="clientes", data=nuevo_df)

# Inicialización de sesión
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

# 2. SEGURIDAD DE ACCESO (Validando contra Google Sheets)
if not st.session_state['autenticado']:
    st.title("⚖️ Acceso al Estudio LexScout")
    
    try:
        df_socios = leer_socios()
        usuario = st.text_input("Usuario (Socio)")
        clave = st.text_input("Contraseña", type="password")
        
        if st.button("Ingresar al Despacho"):
            # Buscamos si el usuario y clave coinciden en la planilla
            match = df_socios[(df_socios['usuario'] == usuario) & (df_socios['clave'] == clave)]
            if not match.empty:
                st.session_state['autenticado'] = True
                st.session_state['usuario_actual'] = usuario
                st.rerun()
            else:
                st.error("Usuario o clave incorrectos.")
    except Exception as e:
        st.error(f"Error de conexión con la base de datos: {e}")
        st.info("Asegurate de haber pegado los Secrets en Streamlit.")
    st.stop()

# 3. INTERFAZ DEL ESTUDIO
nombre_socio = st.session_state['usuario_actual'].replace('_', ' ').title()
st.title(f"⚖️ LexScout: Despacho Virtual")
st.write(f"Conectado como: **Dr./Dra. {nombre_socio}**")

st.divider()

# 4. GESTIÓN DE EXPEDIENTES (Permanente)
st.subheader("📁 Gestión de Clientes")
nuevo_c = st.text_input("Nombre del nuevo cliente (Ej: Perez Juan)")

if st.button("Crear Expediente Permanente"):
    if nuevo_c:
        try:
            guardar_cliente_db(nuevo_c)
            st.success(f"✅ Cliente '{nuevo_c}' guardado en la base de datos de Google.")
            st.rerun()
        except Exception as e:
            st.error(f"No se pudo guardar: {e}")
    else:
        st.warning("Escriba el nombre del cliente.")

st.divider()

# 5. LISTADO Y CARGA DE ARCHIVOS
try:
    df_clientes = leer_clientes()
    if not df_clientes.empty:
        lista_nombres = df_clientes['nombre_cliente'].tolist()
        cliente_sel = st.selectbox("Seleccione el cliente para trabajar:", sorted(lista_nombres))
        
        st.write(f"### 📂 Expediente: {cliente_sel}")
        archivo = st.file_uploader(f"Subir PDF para {cliente_sel}", type="pdf")
        
        if archivo:
            st.success(f"Documento '{archivo.name}' recibido.")
            st.info("La IA analizará este archivo cuando activemos la API de OpenAI.")
    else:
        st.info("Aún no hay expedientes creados en la base de datos.")
except:
    st.warning("No se pudo cargar la lista de clientes.")

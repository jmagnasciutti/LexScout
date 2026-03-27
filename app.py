import streamlit as st
import os

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="LexScout: Inteligencia Legal", page_icon="⚖️")

# 2. ASEGURAR CARPETAS (Evita el error rojo)
if not os.path.exists("clientes"):
    os.makedirs("clientes")

# 3. SEGURIDAD DE ACCESO
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.title("⚖️ Acceso al Estudio LexScout")
    usuario = st.text_input("Usuario (Socio)")
    clave = st.text_input("Contraseña", type="password")
    if st.button("Ingresar al Despacho"):
        if usuario == "jose_luis" and clave == "boca2026":
            st.session_state['autenticado'] = True
            st.rerun()
        else:
            st.error("Usuario o clave incorrectos")
    st.stop()

# 4. INTERFAZ DEL ESTUDIO
st.title(f"Bienvenido, Dr. {st.session_state.get('usuario_actual', 'José Luis')}")

st.subheader("📁 Gestión de Clientes")
nuevo_c = st.text_input("Nombre del nuevo cliente")
if st.button("Crear Expediente"):
    if nuevo_c:
        os.makedirs(os.path.join("clientes", nuevo_c), exist_ok=True)
        st.success(f"Expediente de {nuevo_c} creado correctamente.")
        st.rerun()

st.divider()

# 5. LISTADO DE TRABAJO
clientes = os.listdir("clientes")
if clientes:
    cliente_sel = st.selectbox("Seleccione cliente para trabajar:", clientes)
    st.write(f"### Carpeta actual: {cliente_sel}")
    archivo = st.file_uploader("Subir PDF para analizar", type="pdf")
    if archivo:
        st.success("Archivo cargado. (Esperando activación de OpenAI)")
else:
    st.info("No hay clientes cargados todavía.")

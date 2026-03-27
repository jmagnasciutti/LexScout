import streamlit as st
import os

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="LexScout: Inteligencia Legal", page_icon="⚖️")

# Asegurar que las variables de sesión existan de entrada
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False
if 'usuario_actual' not in st.session_state:
    st.session_state['usuario_actual'] = ""

# 2. ASEGURAR CARPETA RAÍZ
if not os.path.exists("clientes"):
    os.makedirs("clientes", exist_ok=True)

# 3. SEGURIDAD DE ACCESO (Gestión de Socios)
if not st.session_state['autenticado']:
    st.title("⚖️ Acceso al Estudio LexScout")
    
    # Base de datos de socios
    socios = {
        "jose_luis": "river2026",      # Tu nueva clave de River
        "pablo_martinez": "pablo_lex"   # Clave para el Dr. Pablo
    }

    usuario = st.text_input("Usuario (Socio)")
    clave = st.text_input("Contraseña", type="password")
    
    if st.button("Ingresar al Despacho"):
        if usuario in socios and clave == socios[usuario]:
            st.session_state['autenticado'] = True
            st.session_state['usuario_actual'] = usuario
            st.success(f"Bienvenido, Dr. {usuario.replace('_', ' ').title()}")
            st.rerun()
        else:
            st.error("Usuario o clave incorrectos. Verifique sus credenciales.")
    st.stop() # Detiene la ejecución aquí si no está logueado

# 4. INTERFAZ DEL ESTUDIO (Solo llegamos acá si pasó el login)
nombre_socio = st.session_state['usuario_actual'].replace('_', ' ').title()
st.title(f"⚖️ LexScout: Despacho Virtual")
st.write(f"Conectado como: **Dr. {nombre_socio}**")

st.divider()

# 5. GESTIÓN DE EXPEDIENTES
st.subheader("📁 Gestión de Clientes")
nuevo_c = st.text_input("Nombre del nuevo cliente (Ej: Perez Juan)")

if st.button("Crear Carpeta de Expediente"):
    if nuevo_c:
        try:
            path_destino = os.path.join("clientes", nuevo_c)
            if not os.path.exists(path_destino):
                os.makedirs(path_destino)
                st.success(f"✅ Carpeta creada: '{nuevo_c}'")
                st.rerun()
            else:
                st.warning("⚠️ Ya existe un expediente con ese nombre.")
        except Exception as e:
            st.error(f"❌ Error técnico: {e}")
    else:
        st.warning("Escriba el nombre del cliente primero.")

st.divider()

# 6. LISTADO Y CARGA DE ARCHIVOS
try:
    lista_clientes = [f for f in os.listdir("clientes") if os.path.isdir(os.path.join("clientes", f))]
except:
    lista_clientes = []

if lista_clientes:
    cliente_sel = st.selectbox("Seleccione el cliente para trabajar:", sorted(lista_clientes))
    st.write(f"### 📂 Expediente: {cliente_sel}")
    
    archivo = st.file_uploader(f"Subir PDF para {cliente_sel}", type="pdf")
    
    if archivo:
        st.success(f"Documento '{archivo.name}' recibido.")
        st.info("La IA analizará este archivo cuando se active la API Key de OpenAI.")
else:
    st.info("Aún no hay expedientes creados.")

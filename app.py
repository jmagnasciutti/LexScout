import streamlit as st
import os

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="LexScout: Inteligencia Legal", page_icon="⚖️")

# 2. ASEGURAR CARPETA RAÍZ
# Esto crea la carpeta 'clientes' apenas arranca el sistema para evitar errores.
if not os.path.exists("clientes"):
    try:
        os.makedirs("clientes")
    except Exception as e:
        st.error(f"Error crítico al iniciar: {e}")

# 3. SEGURIDAD DE ACCESO
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.title("⚖️ Acceso al Estudio LexScout")
    st.info("Bienvenido, Dr. Identifíquese para ingresar al despacho virtual.")
    
    usuario = st.text_input("Usuario (Socio)")
    clave = st.text_input("Contraseña", type="password")
    
    if st.button("Ingresar al Despacho"):
        if usuario == "jose_luis" and clave == "boca2026":
            st.session_state['autenticado'] = True
            st.rerun()
        else:
            st.error("Usuario o clave incorrectos. Intente nuevamente.")
    st.stop()

# 4. INTERFAZ DEL ESTUDIO (Solo se ve si está autenticado)
st.title("⚖️ LexScout: Despacho Virtual")
st.write(f"Conectado como: **Dr. José Luis**")

st.divider()

# 5. GESTIÓN DE CLIENTES
st.subheader("📁 Gestión de Expedientes")
nuevo_c = st.text_input("Nombre del nuevo cliente (Ej: Perez Juan)")

if st.button("Crear Carpeta de Expediente"):
    if nuevo_c:
        try:
            # Intentamos crear la carpeta del cliente dentro de 'clientes'
            path_destino = os.path.join("clientes", nuevo_c)
            if not os.path.exists(path_destino):
                os.makedirs(path_destino)
                st.success(f"✅ Carpeta creada: '{nuevo_c}'")
                st.rerun() # Refresca para que aparezca en la lista
            else:
                st.warning("⚠️ Ya existe un expediente con ese nombre.")
        except Exception as e:
            st.error(f"❌ Error al crear la carpeta: {e}")
    else:
        st.warning("Escriba el nombre del cliente primero.")

st.divider()

# 6. LISTADO Y CARGA DE ARCHIVOS
# Listamos solo las carpetas reales dentro de 'clientes'
try:
    lista_clientes = [f for f in os.listdir("clientes") if os.path.isdir(os.path.join("clientes", f))]
except:
    lista_clientes = []

if lista_clientes:
    cliente_sel = st.selectbox("Seleccione el cliente para trabajar:", lista_clientes)
    
    st.write(f"### 📂 Carpeta actual: {cliente_sel}")
    
    archivo = st.file_uploader(f"Subir PDF para {cliente_sel}", type="pdf")
    
    if archivo:
        st.success(f"Documento '{archivo.name}' recibido.")
        st.info("Nota: El análisis con IA se activará una vez configurada la API Key de OpenAI.")
        
        if st.button("📥 Procesar para NotebookLM"):
            st.write("Generando resumen estructural...")
else:
    st.info("Aún no hay expedientes creados. Use el campo de arriba para crear el primero.")

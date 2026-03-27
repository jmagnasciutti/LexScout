import streamlit as st
import os
import json
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="LexScout: Inteligencia Legal", page_icon="⚖️")

# --- SIMULACIÓN DE BASE DE DATOS DE SOCIOS ---
SOCIOS = {
    "jose_luis": "boca2026",
    "socio2": "estudio123",
    "socio3": "estudio456"
}

# --- FUNCIONES DE CONTROL ---
def verificar_login(user, pwd):
    if user in SOCIOS and SOCIOS[user] == pwd:
        return True
    return False

# --- INTERFAZ DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.title("⚖️ Acceso al Estudio LexScout")
    usuario = st.text_input("Usuario (Socio)")
    clave = st.text_input("Contraseña", type="password")
    
    if st.button("Ingresar al Despacho"):
        if verificar_login(usuario, clave):
            st.session_state['autenticado'] = True
            st.session_state['usuario_actual'] = usuario
            st.rerun()
        else:
            st.error("Credenciales incorrectas. Verifique con sus socios.")
else:
    # --- INTERFAZ PRINCIPAL (YA LOGUEADO) ---
    st.sidebar.title(f"Bienvenido, Dr. {st.session_state['usuario_actual']}")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state['autenticado'] = False
        st.rerun()

    st.title("⚖️ LexScout: Gestión y Análisis IA")

    # --- MÓDULO DE VENCIMIENTOS (ALERTAS) ---
    st.warning("⚠️ PROXIMOS VENCIMIENTOS: Traslado demanda (Perez) - 48hs restantes")

    # --- GESTIÓN DE CLIENTES ---
    st.subheader("📁 Carpetas de Clientes")

    # Aseguramos que la carpeta raíz 'clientes' exista siempre para evitar errores
    if not os.path.exists("clientes"):
        os.makedirs("clientes")

    # Formulario para crear un cliente nuevo
    cliente_nuevo = st.text_input("Crear nuevo cliente (Nombre y Apellido)")
    if st.button("Crear Carpeta"):
        if cliente_nuevo:
            path = os.path.join("clientes", cliente_nuevo)
            if not os.path.exists(path):
                os.makedirs(path)
                st.success(f"Carpeta creada para: {cliente_nuevo}")
                st.rerun() # Esto refresca la lista automáticamente
            else:
                st.info("Ese cliente ya existe.")
        else:
            st.warning("Por favor, ingresá un nombre para el cliente.")

    st.divider() # Una línea para separar

    # --- SELECCIÓN DE CLIENTE ---
    lista_clientes = os.listdir("clientes")
    
    if lista_clientes:
        # Aquí creamos el selector que te faltaba
        cliente_sel = st.selectbox("Seleccione un Cliente para trabajar:", lista_clientes)
        
        st.write(f"### Trabajando en el expediente de: {cliente_sel}")
        archivo = st.file_uploader(f"Subir PDF para {cliente_sel}", type="pdf")
        
        if archivo:
            st.success(f"Archivo '{archivo.name}' listo para analizar.")
            # Recordatorio del saldo de OpenAI
            st.info("Nota: La IA analizará este archivo cuando habilites el saldo en OpenAI.")
            
            if st.button("📥 Descargar Resumen para NotebookLM"):
                st.write("Generando archivo para Google NotebookLM...")
    else:
        st.info("Aún no hay clientes creados. Empiece por crear uno arriba para habilitar la subida de archivos.")

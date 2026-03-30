import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import tempfile
from datetime import datetime
import google.generativeai as genai

# --- 1. CONFIGURACIÓN Y ESTÉTICA PROFESIONAL ---
st.set_page_config(page_title="LexScout", page_icon="⚖️", layout="wide")

ADMIN_USER = "jose_luis" 

st.markdown("""
    <style>
    header, footer, #MainMenu {visibility: hidden !important;}
    .stDeployButton {display:none !important;}
    [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {display: none !important;}
    .stApp { background-color: #ecedf0; }
    h1, h2, h3 { color: #0c1b33 !important; font-family: 'Times New Roman', serif; font-weight: 800; }
    [data-testid="stSidebar"] { background-color: #081222; border-right: 5px solid #a6894a; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    div.stButton > button {
        background-color: #ffffff; color: #081222; border: 2px solid #a6894a;
        font-weight: 700; transition: 0.3s;
    }
    div.stButton > button:hover { background-color: #081222; color: #ffffff; }
    .resumen-card {
        background-color: #ffffff; padding: 30px; border-radius: 4px;
        border-top: 10px solid #a6894a; box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de conexión: {e}"); st.stop()

# --- 3. LOGIN BLINDADO ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center; margin-top: 50px;'>L E X S C O U T</h1>", unsafe_allow_html=True)
    df_socios = conn.read(worksheet="usuarios", ttl=0)
    col1, col2, col3 = st.columns([1,1.2,1])
    with col2:
        u_input = st.text_input("Usuario")
        c_input = st.text_input("Clave", type="password")
        if st.button("INGRESAR", use_container_width=True):
            u_final = u_input.strip().lower()
            c_final = c_input.strip()
            match = df_socios[(df_socios['usuario'].str.strip().str.lower() == u_final) & (df_socios['clave'].astype(str).str.strip() == c_final)]
            if not match.empty:
                st.session_state['autenticado'], st.session_state['usuario_actual'] = True, u_final
                st.rerun()
            else: st.error("Credenciales Incorrectas.")
    st.stop()

# --- 4. CARGA DE DATOS ---
df_clientes = conn.read(worksheet="clientes", ttl=0)
if 'estado' not in df_clientes.columns: df_clientes['estado'] = 'Activo'

# --- 5. INTERFAZ PRINCIPAL ---
st.markdown("<h1 style='text-align: center; letter-spacing: 5px;'>LEXSCOUT</h1>", unsafe_allow_html=True)
st.divider()

col_principal, col_derecha = st.columns([2.8, 1], gap="medium")

with col_derecha:
    st.markdown("### 🗄️ EXPEDIENTES")
    vista = st.radio("Filtro:", ["Activos", "Archivados"], horizontal=True, label_visibility="collapsed")
    df_filtrado = df_clientes[df_clientes['estado'].fillna('Activo') == ('Activo' if vista == "Activos" else 'Archivado')]
    for idx, row in df_filtrado.iterrows():
        if st.button(f"📁 {row['nombre_cliente']}", key=f"btn_{idx}", use_container_width=True):
            st.session_state['cliente_sel'] = row['nombre_cliente']
            st.rerun()

with col_principal:
    if 'cliente_sel' in st.session_state:
        cliente_actual = st.session_state['cliente_sel']
        datos_c = df_clientes[df_clientes['nombre_cliente'] == cliente_actual].iloc[0]
        st.markdown(f"## Expediente: {cliente_actual}")
        
        # MOSTRAR SINOPSIS ACTUAL
        res_txt = datos_c['resumen_caso'] if 'resumen_caso' in df_clientes.columns and pd.notna(datos_c['resumen_caso']) else "⚠️ Sin sinopsis. Suba un documento abajo para analizar."
        venc_txt = datos_c['vencimiento'] if 'vencimiento' in df_clientes.columns and pd.notna(datos_c['vencimiento']) else "Sin fecha."

        st.markdown(f"""
            <div class="resumen-card">
                <h4 style='margin-top:0; color:#081222;'>SINOPSIS ESTRATÉGICA</h4>
                <p style='color: #2d3748; line-height: 1.8; font-size: 16px;'>{res_txt}</p>
                <hr style='border: 0.5px solid #eee; margin: 20px 0;'>
                <p style='font-size: 14px; color: #a6894a;'><b>PRÓXIMO VENCIMIENTO:</b> {venc_txt}</p>
            </div>
        """, unsafe_allow_html=True)
        
        if pd.notna(datos_c.get('Link Notebooklm')):
            st.link_button("📜 ABRIR LIBRO EN NOTEBOOKLM", datos_c['Link Notebooklm'], use_container_width=True)
        
        st.divider()

        # --- MOTOR DE ANÁLISIS GEMINI ---
        st.markdown("### 📥 ANALIZAR NUEVA ACTUACIÓN")
        st.caption("Subí un PDF (demanda, cédula, proveído) para que la IA redacte la Sinopsis y busque fechas.")
        archivo = st.file_uploader("Subir PDF", type="pdf", label_visibility="collapsed")
        
        if archivo and "GEMINI_API_KEY" in st.secrets:
            if st.button("🚀 GENERAR SINOPSIS CON IA", use_container_width=True):
                with st.spinner("⚖️ Gemini analizando pieza procesal..."):
                    try:
                        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            tmp.write(archivo.getvalue()); t_path = tmp.name
                        
                        doc_ia = genai.upload_file(path=t_path, mime_type="application/pdf")
                        prompt = """
                        Actuá como un prosecretario jurídico experto. Analizá este documento y extraé:
                        1. Un resumen ejecutivo de la situación procesal (máximo 4 líneas).
                        2. La próxima fecha de vencimiento o plazo legal (formato DD/MM/AAAA). 
                        Respondé con el resumen primero, y al final escribí estrictamente: 'FECHA: DD/MM/AAAA'.
                        Si no hay fecha clara, poné 'FECHA: Sin fecha'.
                        """
                        response = model.generate_content([prompt, doc_ia])
                        texto_ia = response.text
                        
                        # Procesar la respuesta para separar resumen de fecha
                        res_ia = texto_ia.split("FECHA:")[0].strip()
                        fec_ia = texto_ia.split("FECHA:")[1].strip() if "FECHA:" in texto_ia else "Sin fecha"
                        
                        # Actualizar Base de Datos (Columnas resumen_caso y vencimiento)
                        if 'resumen_caso' not in df_clientes.columns: df_clientes['resumen_caso'] = ""
                        if 'vencimiento' not in df_clientes.columns: df_clientes['vencimiento'] = ""

                        df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'resumen_caso'] = res_ia
                        if fec_ia != "Sin fecha":
                            df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'vencimiento'] = fec_ia
                        
                        conn.update(worksheet="clientes", data=df_clientes)
                        st.success("✅ Expediente actualizado exitosamente.")
                        os.remove(t_path)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Falla en el análisis: {e}")
    else:
        st.markdown("<div style='text-align:center; padding-top:100px; color:#aaa;'><h3>Seleccioná un caso del archivo</h3></div>", unsafe_allow_html=True)

# --- 6. BARRA LATERAL (ADMIN) ---
with st.sidebar:
    st.markdown(f"👤 **Usuario:** {st.session_state['usuario_actual']}")
    st.divider()
    if st.session_state['usuario_actual'] == ADMIN_USER:
        st.markdown("### ⚙️ ADMINISTRACIÓN")
        with st.expander("➕ NUEVO EXPEDIENTE"):
            n = st.text_input("Nombre Cliente")
            l = st.text_input("Link Notebook")
            if st.button("REGISTRAR"):
                if n:
                    nueva = pd.DataFrame([{"nombre_cliente": n, "Link Notebooklm": l, "estado": "Activo"}])
                    df_upd = pd.concat([df_clientes, nueva], ignore_index=True)
                    conn.update(worksheet="clientes", data=df_upd)
                    st.success("Registrado"); st.rerun()

        if 'cliente_sel' in st.session_state:
            if st.button("📦 ARCHIVAR", use_container_width=True):
                df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'estado'] = 'Archivado'
                conn.update(worksheet="clientes", data=df_clientes)
                st.rerun()
            with st.expander("🚨 ELIMINAR"):
                if st.button("BORRAR AHORA", type="primary", use_container_width=True):
                    df_f = df_clientes[df_clientes['nombre_cliente'] != cliente_actual]
                    conn.update(worksheet="clientes", data=df_f)
                    del st.session_state['cliente_sel']; st.rerun()
    else:
        st.info("Modo de consulta habilitado.")

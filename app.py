import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="LexScout Dashboard", page_icon="⚖️", layout="wide")
ADMIN_USER = "jose_luis" 

st.markdown("""
    <style>
    header, footer, #MainMenu {visibility: hidden !important;}
    .stApp { background-color: #ecedf0; }
    h1, h2, h3 { color: #0c1b33 !important; font-family: 'Times New Roman', serif; font-weight: 800; }
    [data-testid="stSidebar"] { background-color: #081222; border-right: 5px solid #a6894a; }
    
    /* Estilo para las tarjetas del Dashboard */
    .metric-card {
        background-color: #ffffff; padding: 20px; border-radius: 8px;
        text-align: center; border-top: 5px solid #a6894a;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .vigia-card {
        background-color: #f8f9fa; padding: 15px; border-radius: 4px;
        border-left: 10px solid #2ecc71; margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)
df_clientes = conn.read(worksheet="clientes", ttl=0).fillna("")

# --- 3. DASHBOARD SUPERIOR (RESUMEN DE GESTIÓN) ---
st.markdown("<h1 style='text-align: center; letter-spacing: 5px;'>LEXSCOUT</h1>", unsafe_allow_html=True)

# Calculamos estadísticas para el tablero
total_causas = len(df_clientes)
urgentes = df_clientes['Informe_Vigia'].str.contains("🔴").sum()
novedades = df_clientes['Informe_Vigia'].str.contains("🟡").sum()

col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    st.markdown(f"<div class='metric-card'><h4>TOTAL CAUSAS</h4><h2>{total_causas}</h2></div>", unsafe_allow_html=True)
with col_m2:
    st.markdown(f"<div class='metric-card'><h4>🔴 URGENTES</h4><h2>{urgentes}</h2></div>", unsafe_allow_html=True)
with col_m3:
    st.markdown(f"<div class='metric-card'><h4>🟡 NOVEDADES</h4><h2>{novedades}</h2></div>", unsafe_allow_html=True)

st.divider()

# --- 4. INTERFAZ PRINCIPAL ---
col_p, col_d = st.columns([2.8, 1], gap="medium")

with col_d:
    st.markdown("### 🗄️ EXPEDIENTES")
    for idx, row in df_clientes.iterrows():
        # Lógica de Semáforo: Buscamos el emoji en el informe del Vigía
        emoji = "⚪" # Por defecto gris
        if "🔴" in row['Informe_Vigia']: emoji = "🔴"
        elif "🟡" in row['Informe_Vigia']: emoji = "🟡"
        elif "🟢" in row['Informe_Vigia']: emoji = "🟢"
        
        if st.button(f"{emoji} {row['nombre_cliente']}", key=f"btn_{idx}", use_container_width=True):
            st.session_state['cliente_sel'] = row['nombre_cliente']
            st.rerun()

with col_p:
    if 'cliente_sel' in st.session_state:
        c_sel = st.session_state['cliente_sel']
        datos = df_clientes[df_clientes['nombre_cliente'] == c_sel].iloc[0]
        st.markdown(f"## {c_sel}")
        
        # Informe del Vigía (ahora corto y con semáforo)
        if datos['Informe_Vigia']:
            st.markdown(f"""
                <div class="vigia-card">
                    <h4 style='margin-top:0;'>🤖 REPORTE VIGÍA</h4>
                    <p>{datos['Informe_Vigia']}</p>
                </div>
            """, unsafe_allow_html=True)
            
        st.info(f"**Sinopsis Estratégica:** {datos['resumen_caso']}")
    else:
        st.info("Seleccioná un expediente con semáforo para revisar las novedades.")

# MOTOR DE SINCRONIZACIÓN (VERSIÓN BLINDADA)
        st.markdown("### 📥 ANALIZAR PIEZA CLAVE")
        st.caption("Suba el documento principal para que la IA genere la Sinopsis Estratégica y detecte Vencimientos.")
        
        archivo = st.file_uploader("Cargar PDF", type="pdf", label_visibility="collapsed")
        
        if archivo and "OPENAI_API_KEY" in st.secrets:
            with st.spinner("⚖️ LexScout procesando..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(archivo.getvalue())
                    tmp_path = tmp.name
                
                try:
                    loader = PyPDFLoader(tmp_path)
                    docs = loader.load()
                    # Tomamos el contenido para el resumen
                    texto_para_analizar = docs[0].page_content[:6000] 
                    
                    llm = ChatOpenAI(model="gpt-4o-mini", api_key=st.secrets["OPENAI_API_KEY"], temperature=0)
                    
                    # Pedimos el resumen de forma ultra-directa
                    respuesta_resumen = llm.invoke(f"Como abogado, resume este caso en 4 líneas máximo: {texto_para_analizar}")
                    respuesta_venc = llm.invoke(f"Busca una fecha de vencimiento o plazo legal en este texto. Responde SOLO la fecha en formato DD/MM/AAAA. Si no hay, responde 'Sin fecha': {texto_para_analizar}")

                    # ACTUALIZACIÓN EN LA BASE DE DATOS
                    df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'resumen_caso'] = respuesta_resumen.content
                    
                    fecha_detectada = respuesta_venc.content.strip()
                    if len(fecha_detectada) <= 10 and "/" in fecha_detectada:
                        df_clientes.loc[df_clientes['nombre_cliente'] == cliente_actual, 'vencimiento'] = fecha_detectada
                    
                    # Escribimos en el Sheet
                    conn.update(worksheet="clientes", data=df_clientes)
                    
                    st.success("✅ Ficha del expediente actualizada correctamente.")
                    os.remove(tmp_path)
                    st.rerun() # Esto actualiza la vista para que el resumen aparezca arriba
                except Exception as e:
                    st.error(f"Error técnico en el análisis: {e}")

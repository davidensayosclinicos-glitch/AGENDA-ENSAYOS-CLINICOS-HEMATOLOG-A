"""
Panel de análisis de protocolos con IA (OpenAI GPT-4).
Este módulo proporciona funciones para integrar en la aplicación Streamlit principal.
"""

import streamlit as st
import os
from pathlib import Path
from ia_protocoles import ProtocoloAnalyzer, get_api_key, list_protocol_files


def render_protocol_analyzer_section():
    """
    Renderiza la sección completa de análisis de protocolos con IA.
    Debe ser llamada desde la aplicación principal.
    """
    
    st.header("🤖 Análisis de Protocolos con IA")
    
    # Aviso importante
    st.info(
        "📌 **Nota**: Asegúrate de haber configurado tu API key de OpenAI. "
        "Consulta las instrucciones más abajo.",
        icon="ℹ️"
    )
    
    # Sección de configuración
    with st.expander("⚙️ Configuración de API Key", expanded=False):
        st.markdown("""
        ### Cómo configurar tu API key:
        
        **Opción 1: Usar archivo `.streamlit/secrets.toml` (RECOMENDADO)**
        1. Crea la carpeta `.streamlit` en tu proyecto si no existe
        2. Crea o edita el archivo `.streamlit/secrets.toml`
        3. Añade tu API key:
           ```toml
           openai_api_key = "sk-..."
           ```
        4. Reinicia la aplicación
        
        **Opción 2: Variable de entorno**
        ```bash
        export OPENAI_API_KEY="sk-..."
        ```
        
        **Obtener tu API key:**
        1. Ve a https://platform.openai.com/api-keys
        2. Crea una nueva API key
        3. Cópiala y guárdala de forma segura
        
        ⚠️ **Seguridad**: Nunca compartas tu API key públicamente
        """)
    
    # Obtener API key
    api_key = get_api_key()
    
    if not api_key:
        st.error(
            "❌ API key no configurada. Por favor, configura tu API key siguiendo "
            "las instrucciones en la sección de Configuración arriba.",
            icon="❌"
        )
        return
    
    # API key configurada
    st.success("✅ API key configurada correctamente", icon="✅")
    
    # Tabs para diferentes funcionalidades
    tab1, tab2, tab3 = st.tabs([
        "📖 Analizar Protocolo",
        "🔍 Extraer Información",
        "❓ Preguntas Comunes"
    ])
    
    # TAB 1: Análisis libre
    with tab1:
        st.subheader("Análisis de Protocolo")
        
        # Listar protocolos disponibles
        protocol_files = list_protocol_files()
        
        if not protocol_files:
            st.warning("No se encontraron archivos PDF en la carpeta PROTOCOLOS", 
                      icon="⚠️")
            return
        
        selected_protocol = st.selectbox(
            "Selecciona un protocolo:",
            protocol_files,
            key="protocol_select_tab1"
        )
        
        user_question = st.text_area(
            "¿Qué quieres saber sobre este protocolo?",
            placeholder="Ejemplo: ¿Cuáles son los criterios de inclusión principales? "
                       "o ¿Qué medicamentos se utilizan?",
            height=100
        )
        
        if st.button("🚀 Analizar Protocolo", key="analyze_btn_tab1"):
            if not user_question.strip():
                st.error("Por favor, escribe una pregunta sobre el protocolo")
                return
            
            try:
                with st.spinner("📖 Leyendo protocolo..."):
                    analyzer = ProtocoloAnalyzer(api_key)
                    protocol_path = os.path.join("PROTOCOLOS", selected_protocol)
                    
                    # Extraer texto del PDF
                    protocol_text = analyzer.extract_text_from_pdf(protocol_path)
                
                with st.spinner("🤖 Analizando con IA..."):
                    # Analizar con IA
                    analysis = analyzer.analyze_protocol(
                        protocol_text,
                        user_question
                    )
                
                st.success("✅ Análisis completado")
                st.markdown("### Resultado:")
                st.markdown(analysis)
                
                # Opción para copiar
                st.code(analysis, language="markdown")
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}", icon="❌")
    
    # TAB 2: Extracción automática
    with tab2:
        st.subheader("Extracción Automática de Información")
        st.markdown(
            "Extrae automáticamente información clave del protocolo: "
            "nombre, código, indicación, población, medicamentos, criterios, etc."
        )
        
        protocol_files = list_protocol_files()
        
        selected_protocol = st.selectbox(
            "Selecciona un protocolo:",
            protocol_files,
            key="protocol_select_tab2"
        )
        
        if st.button("📊 Extraer Información", key="extract_btn"):
            try:
                with st.spinner("📖 Leyendo protocolo..."):
                    analyzer = ProtocoloAnalyzer(api_key)
                    protocol_path = os.path.join("PROTOCOLOS", selected_protocol)
                    
                    # Extraer texto del PDF
                    protocol_text = analyzer.extract_text_from_pdf(protocol_path)
                
                with st.spinner("🤖 Extrayendo información..."):
                    # Extraer información
                    info_json = analyzer.extract_protocol_info(protocol_text)
                
                st.success("✅ Información extraída")
                st.markdown("### Información del Protocolo:")
                st.json(info_json)
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}", icon="❌")
    
    # TAB 3: Preguntas comunes
    with tab3:
        st.subheader("Preguntas Comunes sobre Protocolos")
        st.markdown(
            "Haz preguntas predefinidas que típicamente necesitas "
            "responder sobre los protocolos."
        )
        
        protocol_files = list_protocol_files()
        
        selected_protocol = st.selectbox(
            "Selecciona un protocolo:",
            protocol_files,
            key="protocol_select_tab3"
        )
        
        # Preguntas comunes
        common_questions = {
            "Criterios de inclusión y exclusión": 
                "¿Cuáles son los criterios de inclusión y exclusión principales?",
            "Medicamentos e indicaciones":
                "¿Cuáles son los medicamentos principales y para qué indicaciones se usan?",
            "Población de pacientes":
                "¿A qué población de pacientes va dirigido este protocolo? "
                "¿Hay restricciones de edad, género o comorbilidades?",
            "Esquema de tratamiento":
                "¿Cuál es el esquema de tratamiento propuesto? "
                "¿Cuáles son las dosis y la duración?",
            "Objetivos del ensayo":
                "¿Cuáles son los objetivos primarios y secundarios?",
            "Evaluaciones y seguimiento":
                "¿Cuáles son las evaluaciones planificadas y el calendario?",
            "Efectos adversos":
                "¿Cuáles son los efectos adversos más relevantes a monitorizar?",
            "Criterios de terminación":
                "¿Cuáles son los criterios de terminación o discontinuación del tratamiento?"
        }
        
        selected_question_title = st.radio(
            "Selecciona una pregunta:",
            list(common_questions.keys())
        )
        
        selected_question = common_questions[selected_question_title]
        
        if st.button("❓ Responder Pregunta", key="common_question_btn"):
            try:
                with st.spinner("📖 Leyendo protocolo..."):
                    analyzer = ProtocoloAnalyzer(api_key)
                    protocol_path = os.path.join("PROTOCOLOS", selected_protocol)
                    
                    # Extraer texto del PDF
                    protocol_text = analyzer.extract_text_from_pdf(protocol_path)
                
                with st.spinner("🤖 Buscando respuesta..."):
                    # Analizar con IA
                    answer = analyzer.analyze_protocol(
                        protocol_text,
                        selected_question
                    )
                
                st.success("✅ Pregunta respondida")
                st.markdown(f"### {selected_question_title}")
                st.markdown(answer)
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}", icon="❌")


# Función auxiliar para uso en la página principal
def add_protocol_analyzer_to_app(sidebar: bool = False):
    """
    Añade el analizador de protocolos a la aplicación.
    
    Args:
        sidebar: Si True, lo añade a la barra lateral (si es posible)
    """
    if sidebar:
        with st.sidebar:
            render_protocol_analyzer_section()
    else:
        render_protocol_analyzer_section()

"""
Panel de análisis de protocolos con IA (OpenRouter).
Este módulo proporciona funciones para integrar en la aplicación Streamlit principal.
"""

import streamlit as st
import os
from pathlib import Path
from ia_protocoles import ProtocoloAnalyzer, get_api_key, list_protocol_files, PROVEEDORES


def render_protocol_analyzer_section():
    """
    Renderiza la sección completa de análisis de protocolos con IA.
    Debe ser llamada desde la aplicación principal.
    """
    
    st.header("🤖 Análisis de Protocolos con IA")
    
    selected_provider = "openrouter"

    # Selector de modelo de OpenRouter
    modelos_prov = PROVEEDORES[selected_provider]["modelos"]
    selected_model = st.selectbox(
        "Modelo OpenRouter:",
        list(modelos_prov.keys()),
        format_func=lambda k: modelos_prov[k],
        key="ia_model"
    )
    # Sección de configuración
    with st.expander("⚙️ Configuración de API Key", expanded=False):
        st.markdown(f"""
        ### Cómo configurar tu API key para **{PROVEEDORES[selected_provider]['nombre']}**:

        **Opción 1: Usar archivo `.streamlit/secrets.toml` (RECOMENDADO)**
        ```toml
        openrouter_api_key = "sk-or-v1-..."  # OpenRouter
        ```

        **Opción 2: Variables de entorno**
        ```bash
        export OPENROUTER_API_KEY="sk-or-v1-..."
        ```

        **Obtener tu API key de OpenRouter:**
        1. Ve a https://openrouter.ai/keys
        2. Crea una API key
        3. Recomendado: usar `openrouter/auto` para evitar errores de endpoints en modelos free
        4. Si eliges modelos `:free`, pueden quedar temporalmente sin endpoints

        ℹ️ `openrouter/auto` puede consumir saldo según el modelo enroutado.

        ⚠️ **Seguridad**: Nunca compartas tu API key públicamente
        """)
    
    # Obtener API key del proveedor seleccionado
    api_key = get_api_key("openrouter")

    if not api_key:
        st.error(
            f"❌ API key de **{PROVEEDORES[selected_provider]['nombre']}** no configurada. "
            "Sigue las instrucciones en la sección de Configuración.",
            icon="❌"
        )
        return

    st.success(f"✅ API key de {PROVEEDORES[selected_provider]['nombre']} configurada", icon="✅")
    
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
                    analyzer = ProtocoloAnalyzer(api_key, provider=selected_provider, model=selected_model)
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
                    analyzer = ProtocoloAnalyzer(api_key, provider=selected_provider, model=selected_model)
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
                    analyzer = ProtocoloAnalyzer(api_key, provider=selected_provider, model=selected_model)
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

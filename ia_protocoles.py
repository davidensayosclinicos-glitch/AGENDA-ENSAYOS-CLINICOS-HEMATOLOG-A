"""
Módulo para integración con OpenAI GPT-4 para análisis de protocolos médicos.
Gestiona lectura de PDFs, procesamiento con IA y extracción de información.
"""

import os
from typing import Optional, Dict, List
import streamlit as st
from PyPDF2 import PdfReader
from openai import OpenAI


class ProtocoloAnalyzer:
    """Clase para analizar protocolos con OpenAI GPT-4"""
    
    def __init__(self, api_key: str):
        """Inicializa el cliente de OpenAI"""
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"  # Usa GPT-4o (más económico que GPT-4)
        self.max_tokens = 2000
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extrae texto de un archivo PDF.
        
        Args:
            pdf_path: Ruta al archivo PDF
            
        Returns:
            Texto extraído del PDF
        """
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                # Tomar las primeras 10 páginas para no saturar tokens
                pages_to_read = min(10, len(pdf_reader.pages))
                for page_num in range(pages_to_read):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text()
            
            return text[:8000]  # Limitar texto inicial a 8000 caracteres
        
        except Exception as e:
            raise Exception(f"Error al leer PDF: {str(e)}")
    
    def analyze_protocol(self, protocol_text: str, prompt: str) -> str:
        """
        Analiza un protocolo usando GPT-4.
        
        Args:
            protocol_text: Texto del protocolo
            prompt: Pregunta o instrucción específica
            
        Returns:
            Análisis realizado por IA
        """
        try:
            system_message = """Eres un experto médico especializado en hematología y ensayos clínicos. 
Tu tarea es analizar protocolos médicos y proporcionar información clara, 
precisa y útil basada en el contenido del protocolo.
Responde en español y sé conciso pero completo."""
            
            user_message = f"""PROTOCOLO:
{protocol_text}

PREGUNTA/SOLICITUD:
{prompt}

Proporciona una respuesta clara y estruturada."""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=self.max_tokens,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            raise Exception(f"Error en análisis con IA: {str(e)}")
    
    def extract_protocol_info(self, protocol_text: str) -> Dict[str, str]:
        """
        Extrae información clave del protocolo automáticamente.
        
        Args:
            protocol_text: Texto del protocolo
            
        Returns:
            Diccionario con información clave
        """
        try:
            prompt = """Extrae la siguiente información del protocolo en formato JSON:
- nombre_protocolo: Nombre completo del protocolo
- codigo: Código del protocolo (ej: 2245, DREAMM-10)
- indicacion: Indicación médica principal
- poblacion_pacientes: A quién va dirigido
- medicamentos_principales: Medicamentos clave mencionados
- criterios_inclusion: Principales criterios de inclusión (máx 3)
- criterios_exclusion: Principales criterios de exclusión (máx 3)
- objetivo_primario: Objetivo primario del ensayo
- duracion_estimada: Duración del tratamiento/ensayo

Responde SOLO con un JSON válido, sin explicaciones adicionales."""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Eres un experto extrayendo datos de protocolos médicos. Responde en JSON válido."},
                    {"role": "user", "content": f"PROTOCOLO:\n{protocol_text}\n\n{prompt}"}
                ],
                max_tokens=1500,
                temperature=0.2
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            raise Exception(f"Error extrayendo información: {str(e)}")


def get_api_key() -> Optional[str]:
    """
    Obtiene el API key de OpenAI de forma segura desde Streamlit secrets.
    
    Returns:
        API key de OpenAI o None si no está configurado
    """
    try:
        # Intentar obtener de Streamlit secrets
        if "openai_api_key" in st.secrets:
            return st.secrets["openai_api_key"]
        
        # Alternativa: variable de entorno
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            return api_key
        
        return None
    
    except Exception as e:
        st.warning(f"Error obteniendo API key: {str(e)}")
        return None


def list_protocol_files(protocol_dir: str = "PROTOCOLOS") -> List[str]:
    """
    Lista los archivos PDF disponibles en la carpeta de protocolos.
    
    Args:
        protocol_dir: Directorio donde están los protocolos
        
    Returns:
        Lista de nombres de archivos PDF
    """
    if not os.path.exists(protocol_dir):
        return []
    
    pdf_files = [f for f in os.listdir(protocol_dir) 
                 if f.lower().endswith('.pdf')]
    return sorted(pdf_files)

"""
Módulo para integración con IA (OpenAI, Groq u OpenRouter) para análisis de protocolos médicos.
Gestiona lectura de PDFs, procesamiento con IA y extracción de información.
"""

import os
import re
import time
from typing import Optional, Dict, List
import streamlit as st
from PyPDF2 import PdfReader
from openai import OpenAI
from groq import Groq

# Proveedores disponibles
PROVEEDORES = {
    "groq": {
        "nombre": "Groq (LLaMA 3.3 · Gratis)",
        "modelos": {
            "llama-3.3-70b-versatile": "LLaMA 3.3 70B · Versátil (recomendado)",
            "llama-3.1-8b-instant": "LLaMA 3.1 8B · Ultra rápido",
            "mixtral-8x7b-32768": "Mixtral 8x7B · Contexto largo (32k)",
            "gemma2-9b-it": "Gemma 2 9B · Google",
        },
        "modelo_default": "llama-3.3-70b-versatile",
    },
    "openai": {
        "nombre": "OpenAI (GPT-4o · De pago)",
        "modelos": {
            "gpt-4o": "GPT-4o · Más capaz",
            "gpt-4o-mini": "GPT-4o Mini · Económico",
        },
        "modelo_default": "gpt-4o",
    },
    "openrouter": {
        "nombre": "OpenRouter (Modelos Free)",
        "modelos": {
            "meta-llama/llama-3.3-70b-instruct:free": "LLaMA 3.3 70B Instruct · Free",
            "deepseek/deepseek-r1:free": "DeepSeek R1 · Free",
            "mistralai/mistral-7b-instruct:free": "Mistral 7B Instruct · Free",
        },
        "modelo_default": "meta-llama/llama-3.3-70b-instruct:free",
    },
}


class ProtocoloAnalyzer:
    """Analiza protocolos médicos usando OpenAI, Groq u OpenRouter como motor de IA."""

    def __init__(self, api_key: str, provider: str = "groq", model: str = None):
        """
        Inicializa el analizador.

        Args:
            api_key: API key del proveedor seleccionado.
            provider: "groq" (por defecto), "openai" u "openrouter".
            model: Modelo específico; si None usa el modelo por defecto del proveedor.
        """
        self.provider = provider
        self.model = model or PROVEEDORES[provider]["modelo_default"]
        self.max_tokens = 2000

        if provider == "groq":
            self.client = Groq(api_key=api_key)
        elif provider == "openrouter":
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1"
            )
        else:
            self.client = OpenAI(api_key=api_key)

    @staticmethod
    def _es_error_rate_limit(error: Exception) -> bool:
        """Detecta errores de límite de tasa de forma tolerante entre proveedores."""
        status_code = getattr(error, "status_code", None)
        if status_code == 429:
            return True

        texto = str(error).lower()
        pistas = [
            "error code: 429",
            "'code': 429",
            '"code": 429',
            "rate limit",
            "rate-limit",
            "rate_limited",
            "too many requests",
            "temporarily rate-limited",
        ]
        if any(pista in texto for pista in pistas):
            return True

        # Fallback regex para variantes tipo "code":429 o "status": 429
        return bool(re.search(r'\b(code|status(?:_code)?)\b[\s\":=\']+429\b', texto))

    def _chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
    ):
        """
        Ejecuta chat completion con tolerancia a 429 en OpenRouter:
        reintenta una vez por modelo y hace fallback a otros modelos free.
        """
        # Para OpenAI/Groq mantenemos ejecución directa.
        if self.provider != "openrouter":
            return self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

        modelos_disponibles = list(PROVEEDORES["openrouter"]["modelos"].keys())
        modelos_a_probar = [self.model] + [m for m in modelos_disponibles if m != self.model]
        ultimo_error = None

        for modelo in modelos_a_probar:
            for intento in range(2):
                try:
                    return self.client.chat.completions.create(
                        model=modelo,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                except Exception as e:
                    ultimo_error = e
                    if not self._es_error_rate_limit(e):
                        raise

                    # Reintento breve en el mismo modelo antes de pasar al siguiente.
                    if intento == 0:
                        time.sleep(1.5)
                        continue
                    break

        raise Exception(
            "OpenRouter devolvió límite de tasa (429) en todos los modelos free probados. "
            "Reintenta en unos minutos o cambia a Groq/OpenAI."
        ) from ultimo_error
    
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
        Analiza un protocolo usando el motor de IA configurado.

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
            
            response = self._chat_completion(
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=self.max_tokens,
                temperature=0.7,
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            raise Exception(f"Error en análisis con IA ({self.provider}): {str(e)}")

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
            
            response = self._chat_completion(
                messages=[
                    {"role": "system", "content": "Eres un experto extrayendo datos de protocolos médicos. Responde en JSON válido."},
                    {"role": "user", "content": f"PROTOCOLO:\n{protocol_text}\n\n{prompt}"}
                ],
                max_tokens=1500,
                temperature=0.2,
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            raise Exception(f"Error extrayendo información ({self.provider}): {str(e)}")


def get_api_key(provider: str = "groq") -> Optional[str]:
    """
    Obtiene el API key del proveedor indicado desde Streamlit secrets o variables de entorno.

    Args:
        provider: "groq", "openai" u "openrouter"

    Returns:
        API key o None si no está configurado
    """
    secrets_key = f"{provider}_api_key"          # groq_api_key / openai_api_key / openrouter_api_key
    env_key = f"{provider.upper()}_API_KEY"       # GROQ_API_KEY / OPENAI_API_KEY / OPENROUTER_API_KEY
    try:
        if secrets_key in st.secrets:
            return st.secrets[secrets_key]
        api_key = os.getenv(env_key)
        if api_key:
            return api_key
        return None
    except Exception as e:
        st.warning(f"Error obteniendo API key ({provider}): {str(e)}")
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

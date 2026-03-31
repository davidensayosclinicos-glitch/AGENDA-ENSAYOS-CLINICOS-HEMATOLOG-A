# 🤖 Integración de OpenAI GPT-4 para Análisis de Protocolos

¡Se ha añadido integración con OpenAI GPT-4 a tu aplicación! Ahora puedes analizar protocolos médicos con IA de forma sencilla.

## 🚀 Inicio Rápido

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Obtener tu API Key de OpenAI

1. Ve a https://platform.openai.com/api-keys
2. Inicia sesión con tu cuenta OpenAI (crea una si aún no tienes)
3. Haz clic en "Create new secret key"
4. Copia la clave (aparece solo una vez)

### 3. Configurar API Key (Opción recomendada)

Crea o edita el archivo `.streamlit/secrets.toml`:

```toml
openai_api_key = "sk-..."
```

**Nota importante**: Este archivo NO debe estar en Git (está en `.gitignore`)

### 4. ¡Listo!

Ejecuta tu app de Streamlit como siempre:
```bash
streamlit run agenda-streamlit/app.py
```

---

## 📋 Qué Hace la IA

La integración permite:

### 📖 **Análisis Libre**
- Haz cualquier pregunta sobre los protocolos
- "¿Cuáles son los criterios de inclusión?"
- "¿Qué medicamentos se usan?"
- "¿Cuál es la duración del tratamiento?"

### 🔍 **Extracción Automática**
Extrae automáticamente:
- Nombre y código del protocolo
- Indicación médica
- Población de pacientes
- Medicamentos principales
- Criterios de inclusión/exclusión
- Objetivos primarios
- Duración estimada

### ❓ **Preguntas Comunes**
Responde automáticamente:
- Criterios de inclusión y exclusión
- Medicamentos e indicaciones
- Población de pacientes
- Esquema de tratamiento
- Objetivos del ensayo
- Evaluaciones y seguimiento
- Efectos adversos
- Criterios de terminación

---

## 💰 Costos de API

OpenAI cobra por uso:
- **GPT-4o**: ~0.0015 $ por 1000 tokens (entrada), ~0.006 $ (salida)
- Un análisis típico cuesta 1-5 centavos

Monitorea tu uso en: https://platform.openai.com/account/billing/overview

---

## ⚙️ Configuración Avanzada

### Usar Variable de Entorno
```bash
export OPENAI_API_KEY="sk-..."
streamlit run agenda-streamlit/app.py
```

### Cambiar Modelo
En `ia_protocoles.py`, línea con `self.model`:
```python
self.model = "gpt-4"      # Más potente, más caro
self.model = "gpt-4o"     # Balance calidad-precio (actual)
self.model = "gpt-3.5-turbo"  # Más barato, menos potente
```

### Ajustar Máximo de Tokens
En `ia_protocoles.py`:
```python
self.max_tokens = 4000  # Aumentar para respuestas más largas
```

---

## 🔒 Seguridad

**Nunca hagas esto:**
- ❌ Commits con API key en el código
- ❌ Compartir tu API key
- ❌ Exponer `secrets.toml` en GitHub

**Sí haz esto:**
- ✅ Usa `.streamlit/secrets.toml` (está en `.gitignore`)
- ✅ Usa variables de entorno
- ✅ Monitorea el acceso a tu API key

---

## 📝 Integración en tu App

El analizador ya vendrá integrado en la app. Si quieres personalizarlo:

### Opción 1: En la barra lateral
```python
from streamlit_protocol_ui import add_protocol_analyzer_to_app

add_protocol_analyzer_to_app(sidebar=True)
```

### Opción 2: En el contenido principal
```python
from streamlit_protocol_ui import add_protocol_analyzer_to_app

add_protocol_analyzer_to_app(sidebar=False)
```

### Opción 3: Uso manual
```python
from ia_protocoles import ProtocoloAnalyzer, get_api_key

api_key = get_api_key()
analyzer = ProtocoloAnalyzer(api_key)

# Leer PDF
text = analyzer.extract_text_from_pdf("PROTOCOLOS/ejemplo.pdf")

# Analizar
resultado = analyzer.analyze_protocol(text, "Tu pregunta aquí")

# Extraer información
info = analyzer.extract_protocol_info(text)
```

---

## 🐛 Solución de Problemas

### Error: "API key no configurada"
- Verifica que `secrets.toml` está en `.streamlit/`
- Verifica que contiene: `openai_api_key = "sk-..."`
- Reinicia la app

### Error: "Archivo PDF no encontrado"
- Asegúrate de que los PDFs están en la carpeta `PROTOCOLOS/`
- Usa rutas relativas desde la raíz del proyecto

### Error: "Límite de tokens excedido"
- La función already limita a las primeras 10 páginas
- Si necesitas más, aumenta con cuidado los `max_tokens`

### Respuestas vagas de la IA
- Intenta ser más específico en la pregunta
- Aumenta temperatura en `analyze_protocol` para más variedad
- Usa el modelo "gpt-4" en lugar de "gpt-4o"

---

## 📚 Recursos

- Documentación OpenAI: https://platform.openai.com/docs/
- Guía de prompts: https://platform.openai.com/docs/guides/gpt-best-practices
- Monitoreo de uso: https://platform.openai.com/account/usage/overview

---

¿Preguntas? Consulta la documentación de OpenAI o los comentarios en el código. 🎉

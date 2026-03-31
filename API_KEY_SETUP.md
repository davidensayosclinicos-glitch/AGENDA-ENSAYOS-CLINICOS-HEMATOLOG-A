# Configuración de API Key para OpenAI

Aquí puedes ver las **dos formas** de configurar tu API key:

## ✅ Opción 1: Usando `.streamlit/secrets.toml` (RECOMENDADO)

Esta es la forma más segura y la que Streamlit recomienda.

### Pasos:
1. **Obtén tu API key** en https://platform.openai.com/api-keys
2. **Crea la carpeta** (si no existe): `.streamlit/`
3. **Crea el archivo** `.streamlit/secrets.toml` con este contenido:

```toml
openai_api_key = "sk-tu-api-key-aqui"
```

**Nota**: Reemplaza `sk-tu-api-key-aqui` con tu verdadera API key.

### Ventajas:
- ✅ Archivo **no se sube a Git** (está en `.gitignore`)
- ✅ Funciona en **desarrollo local y en Streamlit Cloud**
- ✅ Fácil de cambiar sin tocar código

---

## 📌 Opción 2: Variable de Entorno (Alternativa)

Si prefieres usar variables de entorno:

```bash
export OPENAI_API_KEY="sk-tu-api-key-aqui"
```

O en tu `.env` (si usas python-dotenv):
```
OPENAI_API_KEY=sk-tu-api-key-aqui
```

---

## 🔒 Seguridad

- **Nunca** hagas commit de `.streamlit/secrets.toml` con tu API key real
- **Nunca** compartas tu API key públicamente
- Monitorea el uso en https://platform.openai.com/account/usage/overview
- Considera crear una API key específica para este proyecto

---

## ❓ Preguntas Frecuentes

**P: ¿Cuánto cuesta usar GPT-4?**
R: ~0.0015 $ por 1000 tokens (entrada) y ~0.006 $ (salida). Un análisis típico cuesta 1-5 centavos.

**P: ¿Puedo usar un modelo más barato?**
R: Sí. En `ia_protocoles.py`, línea 13, cambia:
```python
self.model = "gpt-3.5-turbo"  # Más barato (~10x menos)
```

**P: ¿Mi API key está segura?**
R: Sí, si usas `.streamlit/secrets.toml`. El archivo nunca se envía y Streamlit lo maneja de forma segura.

---

¿Ya tienes tu API key configurada? Entonces puedes empezar a usar el análisis de protocolos 🚀

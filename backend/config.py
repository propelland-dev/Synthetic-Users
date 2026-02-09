"""
Configuración del backend
"""
import os
from pathlib import Path

# Cargar .env si existe (para configuración local sin tocar la UI)
try:
    from dotenv import load_dotenv  # type: ignore

    # Permitimos .env en raíz del repo o dentro de backend/
    _ROOT_DIR = Path(__file__).parent.parent
    load_dotenv(_ROOT_DIR / ".env", override=False)
    load_dotenv(Path(__file__).parent / ".env", override=False)
except Exception:
    # Si python-dotenv no está instalado o falla, seguimos con env vars normales
    pass

# Directorio base del proyecto
BASE_DIR = Path(__file__).parent

# Directorio de almacenamiento
STORAGE_DIR = BASE_DIR / "storage"

# Configuración de LLaMA
LLAMA_CONFIG = {
    "provider": os.getenv("LLAMA_PROVIDER", "ollama"),  # "ollama" o "llama-cpp-python"
    "model": os.getenv("LLAMA_MODEL", "llama3.2:latest"),  # Nombre del modelo en Ollama
    "base_url": os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
    "temperature": float(os.getenv("LLAMA_TEMPERATURE", "0.7")),
    "max_tokens": int(os.getenv("LLAMA_MAX_TOKENS", "1000")),
}

# Configuración AnythingLLM (para usar OpenAI vía AnythingLLM)
# Nota: AnythingLLM expone una API propia. El endpoint de chat por workspace suele ser:
#   /v1/workspace/{slug}/chat   (algunas instalaciones usan /api/v1/...)
ANYTHINGLLM_CONFIG = {
    "provider": "anythingllm",
    "base_url": os.getenv("ANYTHINGLLM_BASE_URL", "http://localhost:3001"),
    "api_key": os.getenv("ANYTHINGLLM_API_KEY", ""),
    "workspace_slug": os.getenv("ANYTHINGLLM_WORKSPACE_SLUG", ""),
    # "query" (RAG) o "chat" (conversación). Default: query
    "mode": os.getenv("ANYTHINGLLM_MODE", "query"),
    # Para evitar rate limits por ráfagas de llamadas (ms entre requests).
    "min_delay_ms": int(os.getenv("ANYTHINGLLM_MIN_DELAY_MS", "500")),
    # Reintentos en 429 (Too Many Requests)
    "max_retries": int(os.getenv("ANYTHINGLLM_MAX_RETRIES", "3")),
}

# Prompts por defecto
DEFAULT_PROMPTS = {
    "perfil": """Eres un asistente que genera perfiles detallados de usuarios sintéticos para investigación.

Este usuario se define por:
- Arquetipo: {arquetipo}
- Comportamiento: {comportamiento}
- Necesidades del asistente: {necesidades}
- Barreras típicas de adopción: {barreras}

Genera un perfil detallado y realista de este usuario, incluyendo:
- Nombre ficticio (uno)
- Personalidad y rasgos psicológicos
- Motivaciones y frustraciones
- Estilo de comunicación
- Cómo toma decisiones y valida información
- Qué le haría confiar o desconfiar del asistente

Sé específico y realista. No inventes datos que contradigan las 3 dimensiones; si falta información, completa con supuestos razonables y explícitalos brevemente.""",
    
    "investigacion": """Eres {nombre_usuario}, un usuario con las siguientes características:
{perfil_usuario}

Estás participando en una investigación sobre el siguiente producto/experiencia:
Nombre: {nombre_producto}
Descripción: {descripcion_producto}

El equipo de investigación ha definido esta investigación así:
{investigacion_descripcion}

Tu tarea es generar un único **resultado de investigación** en texto, en español, que incluya:
- Hallazgos principales
- Fricciones / barreras detectadas
- Necesidades y expectativas
- Recomendaciones accionables

No lo estructures como preguntas y respuestas; entrega un informe compacto y claro."""
}

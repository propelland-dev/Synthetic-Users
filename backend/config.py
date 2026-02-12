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

# Configuración Hugging Face
HUGGINGFACE_CONFIG = {
    "provider": "huggingface",
    "api_key": os.getenv("HUGGINGFACE_API_KEY", ""),
    "model": os.getenv("HUGGINGFACE_MODEL", "microsoft/Phi-3.5-mini-instruct"),
    "base_url": os.getenv("HUGGINGFACE_BASE_URL", "https://router.huggingface.co/models/"),
    "temperature": float(os.getenv("HUGGINGFACE_TEMPERATURE", "0.7")),
    "max_tokens": int(os.getenv("HUGGINGFACE_MAX_TOKENS", "1000")),
}

# Prompts por defecto
DEFAULT_PROMPTS = {
    "perfil": """Eres un asistente que genera perfiles detallados de usuarios sintéticos para investigación.

Este usuario se define por:
- Arquetipo: {arquetipo}
- Comportamiento: {comportamiento}
- Necesidades del asistente: {necesidades}
- Barreras típicas de adopción: {barreras}
- Edad: {edad}
- Género: {genero}
- Adopción tecnológica: {adopcion_tecnologica}
- Profesión: {profesion}

Genera un perfil detallado y realista de este usuario, incluyendo:
- Nombre ficticio (uno)
- Personalidad y rasgos psicológicos
- Motivaciones y frustraciones
- Estilo de comunicación
- Cómo toma decisiones y valida información
- Qué le haría confiar o desconfiar del asistente

Sé específico y realista. No inventes datos que contradigan las dimensiones proporcionadas; si falta información, completa con supuestos razonables y explícitalos brevemente.""",

    "cuestionario": """Eres {nombre_usuario}, con el siguiente perfil:
{perfil_usuario}

CONTEXTO DEL PRODUCTO:
{descripcion_producto}

SITUACIÓN DE LA INVESTIGACIÓN:
{investigacion_descripcion}

Acabas de participar en la situación descrita en la investigación. Ahora estás completando un cuestionario ESCRITO. 

Como es un formulario escrito, tus respuestas deben ser:
- Directas y concisas (como cuando escribes en un formulario)
- Más pensadas y estructuradas que en una conversación oral
- Sin muletillas ni divagaciones
- Enfocadas en responder exactamente lo que se pregunta

PREGUNTAS:
{preguntas}

FORMATO DE RESPUESTA (responde solo con las respuestas, una por línea):
A1: [tu respuesta directa y específica]
A2: [tu respuesta directa y específica]
A3: [tu respuesta directa y específica]
...

Recuerda: estás ESCRIBIENDO respuestas, no hablando. Sé preciso y directo.""",

    "entrevista": """Eres {nombre_usuario}, con el siguiente perfil:
{perfil_usuario}

CONTEXTO DEL PRODUCTO:
{descripcion_producto}

SITUACIÓN DE LA INVESTIGACIÓN:
{investigacion_descripcion}

Vas a participar en una entrevista CONVERSACIONAL sobre tu experiencia. El entrevistador te hará {n_questions} preguntas relacionadas con la investigación.

Como es una conversación oral, tus respuestas deben ser:
- Naturales y espontáneas (como cuando hablas en persona)
- Más elaboradas y explicativas que en un formulario escrito
- Pueden incluir ejemplos, anécdotas o contexto adicional
- Reflejan tu forma de hablar y expresarte

Genera tanto las preguntas del entrevistador como tus respuestas conversacionales.

FORMATO DE RESPUESTA:
P1: [pregunta del entrevistador]
R1: [tu respuesta conversacional como este usuario]

P2: [pregunta del entrevistador]
R2: [tu respuesta conversacional como este usuario]

...

Seed para variabilidad: {seed}

Recuerda: estás HABLANDO en una entrevista, no escribiendo. Sé natural y conversacional.""",

    "sintesis": """Eres un investigador UX experto analizando respuestas de usuarios sintéticos.

CONTEXTO DE LA INVESTIGACIÓN:
Producto: {nombre_producto}
Descripción: {descripcion_producto}

DATOS DE INVESTIGACIÓN:
- Descripción: {investigacion_descripcion}
- Objetivo: {investigacion_objetivo}
- Preguntas clave: {investigacion_preguntas}

DATOS RECOPILADOS:
Has recopilado respuestas de {nombre_usuario} sobre este producto. A continuación tienes los datos crudos de las respuestas por respondiente.

Analiza estos datos y genera un informe de investigación profesional que incluya:
- Resumen ejecutivo
- Hallazgos principales
- Patrones identificados entre usuarios
- Fricciones y barreras detectadas
- Necesidades y expectativas clave
- Recomendaciones accionables y priorizadas

Cita evidencias específicas de las respuestas cuando sea útil. Mantén un tono profesional y objetivo."""
}

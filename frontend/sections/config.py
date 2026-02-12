import streamlit as st
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar config
sys.path.append(str(Path(__file__).parent.parent))
from config import verificar_ollama, verificar_llm, HUGGINGFACE_UI_CONFIG
from utils import cargar_config, existe_config

def render_config():
    st.markdown('<div class="section-title"><span class="material-symbols-outlined">settings</span>Configuración del Sistema</div>', unsafe_allow_html=True)
    
    st.markdown("""
    Configure los prompts internos y la selección del modelo de lenguaje.
    """)
    
    # Cargar configuración guardada si existe
    config_cargada = cargar_config("system") if existe_config("system") else None

    # Selector de proveedor LLM (por defecto AnythingLLM)
    st.markdown("### Proveedor de LLM")
    default_provider = (
        st.session_state.get("system_llm_provider")
        or (config_cargada or {}).get("llm_provider")
        or "anythingllm"
    )
    default_provider = str(default_provider).strip().lower()
    if default_provider not in {"ollama", "anythingllm", "huggingface"}:
        default_provider = "anythingllm"

    llm_provider_label = st.selectbox(
        "Selecciona el proveedor",
        options=["AnythingLLM", "Ollama (local)", "Hugging Face"],
        index=(
            0 if default_provider == "anythingllm" 
            else 2 if default_provider == "huggingface"
            else 1
        ),
        help="AnythingLLM permite usar OpenAI (u otro) a través de tu instancia AnythingLLM. Ollama genera local. Hugging Face usa Inference API."
    )
    
    if llm_provider_label == "AnythingLLM":
        llm_provider = "anythingllm"
    elif llm_provider_label == "Hugging Face":
        llm_provider = "huggingface"
    else:
        llm_provider = "ollama"

    # Guardar el provider en session_state para permitir \"Iniciar\" sin pasar por Guardar
    st.session_state["system_llm_provider"] = llm_provider

    # --- Conexión / verificación ---
    st.markdown("### Estado de Conexión")
        
    if st.button("🔍 Verificar Conexión"):
        with st.spinner("Verificando conexión..."):
            # Construir un system_config mínimo para el check
            payload = {
                "llm_provider": llm_provider,
                "anythingllm_base_url": st.session_state.get("system_anythingllm_base_url") or (config_cargada or {}).get("anythingllm_base_url"),
                "anythingllm_api_key": st.session_state.get("system_anythingllm_api_key") or (config_cargada or {}).get("anythingllm_api_key"),
                "anythingllm_workspace_slug": st.session_state.get("system_anythingllm_workspace_slug") or (config_cargada or {}).get("anythingllm_workspace_slug"),
                "anythingllm_mode": st.session_state.get("system_anythingllm_mode") or (config_cargada or {}).get("anythingllm_mode"),
                "huggingface_api_key": st.session_state.get("system_huggingface_api_key") or (config_cargada or {}).get("huggingface_api_key"),
                "huggingface_model": st.session_state.get("system_huggingface_model") or (config_cargada or {}).get("huggingface_model"),
            }
            status = verificar_llm(payload) if llm_provider in {"anythingllm", "huggingface"} else verificar_ollama()
            st.session_state['llm_status'] = status or {
                "status": "error",
                "message": "No se pudo verificar la conexión (backend no accesible o error de red)."
            }
        
    # Mostrar estado de conexión
    if 'llm_status' in st.session_state and st.session_state['llm_status']:
        status = st.session_state['llm_status']
        status_type = status.get("status", "unknown")
        if status_type == "connected":
            st.success(f"✅ {status.get('message', 'Conectado')}")
        elif status_type == "disconnected":
            st.error(f"❌ {status.get('message', 'No conectado')}")
        elif status_type == "timeout":
            st.error(f"⏱️ {status.get('message', 'Timeout al conectar')}")
        else:
            st.error(f"❌ {status.get('message', 'Error desconocido')}")

    st.markdown("### Parámetros")
        
    col1, col2 = st.columns(2)
    with col1:
        temperatura = st.slider(
            "Temperatura",
            min_value=0.0,
            max_value=2.0,
            value=(config_cargada.get("temperatura", 0.7) if config_cargada else 0.7),
            step=0.1,
            help="Controla la aleatoriedad de las respuestas (0 = determinista, 2 = muy creativo).",
            key="system_temperatura",
        )
    with col2:
        max_tokens = st.number_input(
            "Max Tokens",
            min_value=50,
            max_value=4000,
            value=(config_cargada.get("max_tokens", 1000) if config_cargada else 1000),
            step=50,
            help="Número máximo de tokens en la respuesta.",
            key="system_max_tokens",
        )

    # Campos específicos por proveedor
    if llm_provider == "ollama":
        modelo_path = st.text_input(
            "Ruta del modelo (opcional)",
            value=(config_cargada.get("modelo_path", "") if config_cargada else ""),
            placeholder="Dejar vacío para usar configuración por defecto",
            help="(Opcional) Ruta local del modelo. Normalmente no es necesario con Ollama.",
            key="system_modelo_path",
        )
    elif llm_provider == "huggingface":
        st.info("Configura tu acceso a Hugging Face Inference API en el backend (.env).")
        
        # Lista de modelos desde el archivo de configuración del frontend
        modelos_hf = HUGGINGFACE_UI_CONFIG.get("models_list", [])
        # Modelo por defecto o guardado
        modelo_actual = (st.session_state.get("system_huggingface_model") 
                         or (config_cargada or {}).get("huggingface_model") 
                         or (modelos_hf[0] if modelos_hf else ""))
        
        # Si el modelo actual no está en la lista, lo añadimos como opción personalizada
        if modelo_actual and modelo_actual not in modelos_hf:
            modelos_hf = [modelo_actual] + modelos_hf
            
        modelo_hf_seleccionado = st.selectbox(
            "Selecciona un Modelo Hugging Face",
            options=modelos_hf + ["Otro (especificar...)"],
            index=modelos_hf.index(modelo_actual) if modelo_actual in modelos_hf else 0,
            key="hf_model_selectbox"
        )
        
        if modelo_hf_seleccionado == "Otro (especificar...)":
            st.text_input(
                "Especifica el nombre del modelo",
                value=(modelo_actual if modelo_actual not in modelos_hf else ""),
                placeholder="usuario/modelo",
                help="Nombre del modelo en Hugging Face (ej: mistralai/Mistral-7B-Instruct-v0.3).",
                key="system_huggingface_model",
            )
        else:
            st.session_state["system_huggingface_model"] = modelo_hf_seleccionado
    else:
        st.info("Si ya tienes AnythingLLM configurado en el backend (env/.env), no necesitas rellenar nada aquí.")
        with st.expander("Avanzado: parámetros de AnythingLLM (opcional)"):
            base_default = (config_cargada.get("anythingllm_base_url") if config_cargada else "") or "http://localhost:3001"
            st.text_input(
                "AnythingLLM Base URL",
                value=base_default,
                placeholder="http://localhost:3001",
                help="URL de tu instancia AnythingLLM (self-hosted o desktop).",
                key="system_anythingllm_base_url",
            )
            st.text_input(
                "AnythingLLM API Key",
                value=(config_cargada.get("anythingllm_api_key", "") if config_cargada else ""),
                type="password",
                help="API key generada en AnythingLLM. Se enviará como Authorization: Bearer <key>.",
                key="system_anythingllm_api_key",
            )
            st.text_input(
                "Workspace slug",
                value=(config_cargada.get("anythingllm_workspace_slug", "") if config_cargada else ""),
                placeholder="mi-workspace",
                help="Slug del workspace en AnythingLLM que quieres usar para el chat/query.",
                key="system_anythingllm_workspace_slug",
            )
            st.selectbox(
                "Modo",
                options=["query", "chat"],
                index=(
                    1
                    if str((config_cargada or {}).get("anythingllm_mode") or "chat").strip().lower() == "chat"
                    else 0
                ),
                help="query: usa el modo de consulta/RAG. chat: conversación.",
                key="system_anythingllm_mode",
            )
    
    # Prompts configurables
    st.markdown("### Prompts Configurables")
    
    # Prompt para generar perfil de usuario
    st.markdown("#### Prompt: Generación de Perfil de Usuario")
    prompt_perfil_default = """Eres un asistente que genera perfiles detallados de usuarios sintéticos para investigación.

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

Sé específico y realista. No inventes datos que contradigan las dimensiones proporcionadas; si falta información, completa con supuestos razonables y explícitalos brevemente."""
    
    # Si existe un prompt guardado antiguo (con {edad}/{genero}/etc), usamos el nuevo por defecto
    prompt_perfil_guardado = config_cargada.get("prompt_perfil") if config_cargada else None
    if isinstance(prompt_perfil_guardado, str):
        legacy_markers = ["{edad}", "{genero}", "{ubicacion}", "{experiencia_tecnologica}", "{intereses}"]
        new_markers = ["{arquetipo}", "{comportamiento}", "{necesidades}", "{barreras}", "{adopcion_tecnologica}", "{profesion}"]
        is_legacy = any(m in prompt_perfil_guardado for m in legacy_markers) and not any(m in prompt_perfil_guardado for m in new_markers)
    else:
        is_legacy = False

    prompt_perfil = st.text_area(
        "Prompt para generar perfil de usuario sintético",
        value=(prompt_perfil_default if is_legacy else (prompt_perfil_guardado or prompt_perfil_default)),
        height=200,
        help="Variables disponibles: {arquetipo}, {comportamiento}, {necesidades}, {barreras}, {edad}, {genero}, {adopcion_tecnologica}, {profesion}",
        key="system_prompt_perfil",
    )
    
    # Prompt para cuestionarios
    st.markdown("#### Prompt: Respuesta a Cuestionarios")
    prompt_cuestionario_default = """Eres {nombre_usuario}, con el siguiente perfil:
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

Recuerda: estás ESCRIBIENDO respuestas, no hablando. Sé preciso y directo."""
    
    prompt_cuestionario = st.text_area(
        "Prompt para responder cuestionarios estructurados",
        value=(config_cargada.get("prompt_cuestionario") or prompt_cuestionario_default) if config_cargada else prompt_cuestionario_default,
        height=200,
        help="Variables disponibles: {nombre_usuario}, {perfil_usuario}, {descripcion_producto}, {investigacion_descripcion}, {investigacion_objetivo}, {investigacion_preguntas}, {preguntas}",
        key="system_prompt_cuestionario",
    )

    # Prompt para entrevistas
    st.markdown("#### Prompt: Simulación de Entrevistas")
    prompt_entrevista_default = """Eres {nombre_usuario}, con el siguiente perfil:
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

Recuerda: estás HABLANDO en una entrevista, no escribiendo. Sé natural y conversacional."""
    
    prompt_entrevista = st.text_area(
        "Prompt para simular entrevistas conversacionales",
        value=(config_cargada.get("prompt_entrevista") or prompt_entrevista_default) if config_cargada else prompt_entrevista_default,
        height=200,
        help="Variables disponibles: {nombre_usuario}, {perfil_usuario}, {descripcion_producto}, {investigacion_descripcion}, {investigacion_objetivo}, {investigacion_preguntas}, {n_questions}, {seed}",
        key="system_prompt_entrevista",
    )

    # Prompt para síntesis final
    st.markdown("#### Prompt: Síntesis de Investigación")
    prompt_sintesis_default = """Eres un investigador UX experto analizando respuestas de usuarios sintéticos.

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
    
    prompt_sintesis = st.text_area(
        "Prompt para generar síntesis final de investigación",
        value=(config_cargada.get("prompt_sintesis") or prompt_sintesis_default) if config_cargada else prompt_sintesis_default,
        height=200,
        help="Variables disponibles: {nombre_usuario}, {nombre_producto}, {descripcion_producto}, {investigacion_descripcion}, {investigacion_objetivo}, {investigacion_preguntas}",
        key="system_prompt_sintesis",
    )

    # Prompt para generar ficha de producto
    st.markdown("#### Prompt: Generación de Ficha de Producto")
    prompt_ficha_producto_default = """Eres un asistente de research. Con los datos estructurados de un producto, genera una “Ficha de producto” en español (Markdown), clara y accionable.

DATOS
- Tipo: {producto_tipo}  (nuevo/existente)
- Nombre: {nombre_producto}
- Descripción (input libre): {descripcion_input}
- Problema a resolver: {problema_a_resolver}
- Propuesta de valor: {propuesta_valor}
- Funcionalidades clave: {funcionalidades_clave}
- Canal de soporte: {canal_soporte}
- Productos sustitutivos: {productos_sustitutivos}
- Fuentes a ingestar: {fuentes_a_ingestar}
- Observaciones: {observaciones}
- Riesgos: {riesgos}
- Dependencias: {dependencias}

SI ES EXISTENTE (opcional)
- URL: {url}
- Documentos: {documentos}
- Fotos: {fotos}

REQUISITOS DE SALIDA
- Devuelve SOLO Markdown.
- Incluye secciones: Resumen, Problema, Propuesta de valor, Alcance/No alcance, Funcionalidades clave, Soporte/Operación, Sustitutivos/Alternativas, Riesgos, Dependencias, Fuentes a ingestar, Observaciones, Preguntas abiertas.
- Si falta información, no inventes: marca “(pendiente)” y añade preguntas concretas a “Preguntas abiertas”.
"""

    prompt_ficha_producto = st.text_area(
        "Prompt para generar ficha de producto",
        value=(
            (config_cargada or {}).get("prompt_ficha_producto") or prompt_ficha_producto_default
        ),
        height=220,
        help="Variables disponibles: {producto_tipo}, {nombre_producto}, {descripcion_input}, {problema_a_resolver}, {propuesta_valor}, {funcionalidades_clave}, {canal_soporte}, {productos_sustitutivos}, {fuentes_a_ingestar}, {observaciones}, {riesgos}, {dependencias}, {url}, {documentos}, {fotos}",
        key="system_prompt_ficha_producto",
    )
    
    # Mantener config en sesión siempre actualizada (se persistirá al cambiar de página)
    st.session_state["system_config"] = {
        "llm_provider": llm_provider,
        "temperatura": temperatura,
        "max_tokens": max_tokens,
        "modelo_path": st.session_state.get("system_modelo_path") or "",
        "prompt_perfil": prompt_perfil,
        "prompt_cuestionario": prompt_cuestionario,
        "prompt_entrevista": prompt_entrevista,
        "prompt_sintesis": prompt_sintesis,
        "prompt_ficha_producto": prompt_ficha_producto,
        "anythingllm_base_url": st.session_state.get("system_anythingllm_base_url"),
        "anythingllm_api_key": st.session_state.get("system_anythingllm_api_key"),
        "anythingllm_workspace_slug": st.session_state.get("system_anythingllm_workspace_slug"),
        "anythingllm_mode": st.session_state.get("system_anythingllm_mode"),
        "huggingface_api_key": st.session_state.get("system_huggingface_api_key"),
        "huggingface_model": st.session_state.get("system_huggingface_model"),
    }

    # Acciones
    st.markdown("---")
    if st.button("Restaurar por Defecto", key="config_restore_defaults"):
        st.session_state['system_config'] = None
        for k in [
            "system_llm_provider",
            "system_temperatura",
            "system_max_tokens",
            "system_modelo_path",
            "system_prompt_perfil",
            "system_prompt_cuestionario",
            "system_prompt_entrevista",
            "system_prompt_sintesis",
            "system_prompt_ficha_producto",
            "system_anythingllm_base_url",
            "system_anythingllm_api_key",
            "system_anythingllm_workspace_slug",
            "system_anythingllm_mode",
            "system_huggingface_api_key",
            "system_huggingface_model",
            "llm_status",
        ]:
            st.session_state.pop(k, None)
        st.rerun()

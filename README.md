# Moeve Synthetic Users

Sistema para **definir usuarios sintéticos** (arquetipo + 3 dimensiones), **describir un producto/experiencia**, y ejecutar una **investigación automatizada** con un LLM local (Ollama) que devuelve un **único informe** de resultados.

El flujo está dividido en:
- **Frontend**: Streamlit (UI) para configurar y lanzar la investigación.
- **Backend**: FastAPI (API) que persiste configs/resultados y llama a Ollama.

## Características

- **Usuario sintético por dimensiones**: arquetipo + comportamiento + necesidades + barreras.
- **Producto/experiencia como contexto**: una descripción libre (no limitado a chatbots).
- **Investigación como texto libre**: una descripción/brief (puede incluir preguntas dentro del propio texto).
- **Resultado único**: el backend genera un **informe en texto** (`resultados["resultado"]`).
- **Prompts configurables**: `prompt_perfil` y `prompt_investigacion` editables desde la UI.
- **Persistencia simple**: archivos JSON en `frontend/configs/` (UI) y `backend/storage/` (backend).
- **Exportación**: descarga de resultados a **PDF** desde la UI.

## Estructura del proyecto

```
.
├── frontend/                      # App Streamlit
│   ├── app.py                     # Entry point UI
│   ├── config.py                  # Cliente HTTP hacia el backend
│   ├── utils.py                   # Guardar/cargar configs locales
│   ├── configs/                   # Configs locales (UI)
│   │   ├── arquetipos.json
│   │   ├── config_syntetic_user.json
│   │   ├── config_producto.json
│   │   ├── config_investigacion.json
│   │   └── config_system.json
│   └── sections/                  # Pantallas (render_*)
│       ├── syntetic_users.py
│       ├── product.py
│       ├── research.py
│       ├── results.py
│       └── config.py
├── backend/                       # API FastAPI + lógica
│   ├── api/
│   │   ├── main.py                # App FastAPI
│   │   └── routes/                # Endpoints
│   │       ├── usuario.py
│   │       ├── producto.py
│   │       ├── investigacion.py
│   │       ├── resultados.py
│   │       └── llm.py
│   ├── core/                      # Lógica de negocio
│   │   ├── llm_client.py          # Cliente Ollama
│   │   ├── synthetic_user.py      # Generación de perfil
│   │   └── research_engine.py     # Generación del informe
│   ├── storage/                   # Persistencia del backend (JSON)
│   │   ├── usuarios/
│   │   ├── productos/
│   │   ├── investigaciones/
│   │   └── resultados/
│   └── config.py                  # Defaults + env vars
├── requirements.txt
└── README.md
```

## Requisitos

- **Python**: 3.8+ (probado con 3.13).
- **Ollama** corriendo en local.
- **Modelo** descargado en Ollama (por defecto: `llama3.2:latest`).

## Instalación

### Ollama (local)

- Instalar Ollama: ver `https://ollama.ai`.
- Descargar modelo:

```bash
ollama pull llama3.2:latest
```

- Levantar Ollama (si no lo hace como servicio):

```bash
ollama serve
```

Por defecto: `http://localhost:11434`.

### Proyecto (Python)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Ejecución

### 1) Backend (FastAPI)

```bash
cd backend
uvicorn api.main:app --reload
```

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

### 2) Frontend (Streamlit)

```bash
cd frontend
streamlit run app.py
```

UI: `http://localhost:8501`

## Flujo de uso (end-to-end)

1. **Usuario sintético** (`frontend/sections/syntetic_users.py`)
   - Define: `arquetipo`, `comportamiento`, `necesidades`, `barreras`.
   - Guarda local (`frontend/configs/config_syntetic_user.json`) y envía al backend (`POST /api/usuario`).

2. **Producto** (`frontend/sections/product.py`)
   - Define: `descripcion`.
   - Guarda local (`frontend/configs/config_producto.json`) y envía al backend (`POST /api/producto`).

3. **Investigación** (`frontend/sections/research.py`)
   - Define: `descripcion` (brief). Puedes incluir preguntas en el texto si lo deseas.
   - Guarda local (`frontend/configs/config_investigacion.json`) y envía al backend (`POST /api/investigacion`).

4. **Sistema / prompts** (`frontend/sections/config.py`) **(recomendado)**
   - Ajusta: `llm_provider`, `temperatura`, `max_tokens`.
   - Edita: `prompt_perfil` y **`prompt_investigacion`**.
   - Guarda en `frontend/configs/config_system.json`.

5. **Iniciar investigación**
   - Botón “Iniciar investigación” llama a `POST /api/investigacion/iniciar`.
   - El backend carga la última config guardada (usuario/producto/investigación) desde `backend/storage/`.
   - Se genera:
     - Perfil del usuario (`SyntheticUser.generate_profile`)
     - Informe final (`ResearchEngine.execute`) en `resultados["resultado"]`
   - Se guarda un JSON en `backend/storage/resultados/*_investigacion.json`.

6. **Resultados**
   - Renderiza `resultados["resultado"]` (Markdown) y permite exportar a PDF.

## Configuración

### Variables de entorno (backend)

En `backend/config.py` se leen:

```bash
export OLLAMA_BASE_URL="http://localhost:11434"
export LLAMA_PROVIDER="ollama"
export LLAMA_MODEL="llama3.2:latest"
export LLAMA_TEMPERATURE="0.7"
export LLAMA_MAX_TOKENS="1000"
```

### Variables de entorno (frontend)

En `frontend/config.py`:

```bash
export API_BASE_URL="http://localhost:8000"
```

## Prompts y placeholders soportados

### Prompt de perfil (`prompt_perfil`)

Se formatea con las claves:
- `{arquetipo}`, `{comportamiento}`, `{necesidades}`, `{barreras}`

Nota: el backend mantiene **compatibilidad** con prompts antiguos que usen `{edad}`, `{genero}`, `{ubicacion}`, etc. Si faltan, se sustituyen por `N/A`.

### Prompt de investigación (`prompt_investigacion`)

El backend genera el informe con:
- `{nombre_usuario}`
- `{perfil_usuario}`
- `{nombre_producto}` (si no existe, usa “Producto”)
- `{descripcion_producto}`
- `{investigacion_descripcion}`

Importante: el endpoint `POST /api/investigacion/iniciar` **requiere** que el frontend envíe `system_config.prompt_investigacion` (si no, devuelve 400).

## API (contrato rápido)

### Salud y estado

- `GET /` → estado básico.
- `GET /health` → health check.
- `GET /api/llm/status` → estado de conexión con Ollama (lista modelos, modelo activo, etc.).

### Configuración

- `POST /api/usuario`

```json
{
  "arquetipo": "Explorador",
  "comportamiento": "…",
  "necesidades": "…",
  "barreras": "…"
}
```

- `POST /api/producto`

```json
{ "descripcion": "…" }
```

- `POST /api/investigacion`

```json
{ "descripcion": "…" }
```

### Ejecutar investigación

- `POST /api/investigacion/iniciar`

```json
{
  "system_config": {
    "llm_provider": "ollama",
    "temperatura": 0.7,
    "max_tokens": 1000,
    "prompt_perfil": "…",
    "prompt_investigacion": "…"
  }
}
```

Respuesta (simplificada):

```json
{
  "status": "success",
  "message": "Investigación completada",
  "resultados": {
    "timestamp": "2026-01-29T…",
    "usuario": { "arquetipo": "…", "comportamiento": "…", "necesidades": "…", "barreras": "…" },
    "usuario_nombre": "Explorador",
    "producto": { "descripcion": "…", "nombre_producto": "Producto" },
    "investigacion": { "descripcion": "…" },
    "resultado": "…",
    "resultado_id": "20260129_123456_investigacion.json"
  }
}
```

### Resultados

- `GET /api/resultados` → lista de resultados (ids y metadatos).
- `GET /api/resultados/latest` → JSON del último resultado.
- `GET /api/resultados/{resultado_id}` → JSON de un resultado (id sin `.json`).

## Persistencia de datos

- **Frontend** (`frontend/configs/`): últimos valores usados en la UI.
- **Backend** (`backend/storage/`): histórico de configs y resultados con timestamps.

Recomendación: tratar `backend/storage/` como **datos generados** (no código). Si se versionan, hacerlo de forma intencional.

## Solución de problemas

### “Falta 'prompt_investigacion'…”

El backend exige `prompt_investigacion` al iniciar la investigación.
- Ve a **Configuración** en la UI, guarda la configuración del sistema y vuelve a ejecutar.

### Ollama no conecta

```bash
ollama serve
ollama list
```

Y revisa `OLLAMA_BASE_URL`.

### Frontend no conecta al backend

- Verifica backend en `http://localhost:8000/health`.
- Revisa `API_BASE_URL` (frontend) si cambiaste puertos.

### La investigación tarda mucho o da timeout

- Reduce `max_tokens`.
- Usa un modelo más ligero en Ollama.

## Notas de desarrollo

- No se usa LangChain; el backend llama a Ollama por HTTP (`/api/generate`).
- Actualmente el proveedor soportado es **Ollama** (ChatGPT está preparado pero no implementado en `LLMClient`).

usar docker-compose up --build para levantar el proyecto
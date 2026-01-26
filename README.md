# Moeve Synthetic Users

Sistema para generar y gestionar usuarios sintéticos para investigación de productos. Permite configurar usuarios sintéticos, productos, metodologías de investigación y visualizar resultados de manera integrada.

## 🎯 Características

- **Configuración de Usuarios Sintéticos**: Define parámetros demográficos, intereses y características de usuarios sintéticos
- **Configuración de Producto**: Establece detalles del producto o servicio a evaluar
- **Configuración de Investigación**: Define metodología, objetivos y métricas de investigación
- **Visualización de Resultados**: Dashboard interactivo para analizar resultados y métricas

## 📁 Estructura del Proyecto

```
.
├── frontend/                    # Aplicación Streamlit
│   ├── app.py                  # Aplicación principal
│   ├── config.py               # Configuración de la API
│   └── sections/               # Secciones de la aplicación
│       ├── __init__.py
│       ├── syntetic_users.py   # Sección: Usuarios Sintéticos
│       ├── product.py          # Sección: Producto
│       ├── research.py    # Sección: Investigación
│       └── results.py           # Sección: Resultados
├── backend/                    # API FastAPI
│   └── api/
│       └── main.py             # API principal
├── requirements.txt            # Dependencias del proyecto
└── README.md                   # Este archivo
```

## 🚀 Instalación

### Prerrequisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Pasos de instalación

1. **Clonar el repositorio** (si aplica):
```bash
git clone <repository-url>
cd 202601-Moeve-Syntetic-Users
```

2. **Crear entorno virtual**:
```bash
python3.13 -m venv venv
```

3. **Activar entorno virtual**:
   - En macOS/Linux:
   ```bash
   source venv/bin/activate
   ```
   - En Windows:
   ```bash
   venv\Scripts\activate
   ```

4. **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

## 💻 Uso

### Frontend (Streamlit)

Para ejecutar la aplicación web:

```bash
cd frontend
streamlit run app.py
```

La aplicación estará disponible en: **http://localhost:8501**

#### Navegación

La aplicación cuenta con 4 secciones principales accesibles desde el sidebar:

1. **👥 Usuarios Sintéticos**: Configuración de parámetros para generar usuarios sintéticos
   - Número de usuarios
   - Rango de edad
   - Géneros
   - Ubicaciones geográficas
   - Nivel educativo
   - Ingresos
   - Intereses
   - Experiencia tecnológica

2. **📦 Producto**: Configuración del producto a evaluar
   - Información básica (nombre, categoría, tipo, versión)
   - Descripción y características
   - Precio y modelo de negocio
   - Público objetivo

3. **🔬 Investigación**: Configuración de la metodología de investigación
   - Tipo de investigación
   - Objetivos
   - Duración y frecuencia
   - Métricas a evaluar
   - Preguntas específicas
   - Escenarios de uso

4. **📊 Resultados**: Visualización y análisis de resultados
   - Estado de la investigación
   - Métricas principales
   - Feedback de usuarios
   - Análisis por segmentos
   - Exportación de reportes

### Backend (FastAPI)

Para ejecutar la API:

```bash
cd backend
uvicorn api.main:app --reload
```

La API estará disponible en: **http://localhost:8000**

#### Endpoints disponibles

- `GET /` - Estado de la API
- `POST /api/usuarios` - Guardar configuración de usuarios
- `POST /api/producto` - Guardar configuración de producto
- `POST /api/investigacion` - Guardar configuración de investigación
- `POST /api/investigacion/iniciar` - Iniciar investigación
- `GET /api/resultados` - Obtener resultados

#### Documentación de la API

Una vez que la API esté ejecutándose, puedes acceder a:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## ⚙️ Configuración

### Variables de entorno

Puedes configurar la URL de la API mediante una variable de entorno:

```bash
export API_BASE_URL=http://localhost:8000
```

O modificar directamente el archivo `frontend/config.py`.

## 🔧 Desarrollo

### Estructura de secciones

Cada sección del frontend es un módulo independiente en `frontend/sections/` que exporta una función `render_*()` que contiene toda la lógica de la interfaz.

### Estado de la aplicación

El estado se gestiona mediante `st.session_state` de Streamlit, permitiendo persistir configuraciones entre secciones.

## 📦 Dependencias principales

- **streamlit**: Framework para la aplicación web
- **fastapi**: Framework para la API REST
- **pandas**: Manipulación y análisis de datos
- **uvicorn**: Servidor ASGI para FastAPI
- **requests**: Cliente HTTP para comunicación con la API

Ver `requirements.txt` para la lista completa de dependencias.

## 🛠️ Próximos pasos

- [ ] Implementar integración completa con la API
- [ ] Agregar persistencia de datos
- [ ] Mejorar visualizaciones de resultados
- [ ] Agregar autenticación y autorización
- [ ] Implementar exportación de reportes (PDF, Excel)

## 📝 Licencia

[Especificar licencia si aplica]

## 👥 Contribuidores

[Agregar información de contribuidores si aplica]

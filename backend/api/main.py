"""
API principal FastAPI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import usuario, producto, investigacion, resultados, llm

app = FastAPI(
    title="API de Usuarios Sintéticos",
    description="API para gestionar usuarios sintéticos y ejecutar investigaciones",
    version="1.0.0"
)

# CORS - Permitir requests desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(usuario.router)
app.include_router(producto.router)
app.include_router(investigacion.router)
app.include_router(resultados.router)
app.include_router(llm.router)


@app.get("/")
def read_root():
    """Endpoint raíz"""
    return {
        "message": "API de Usuarios Sintéticos",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
def health_check():
    """Endpoint de health check"""
    return {"status": "healthy"}

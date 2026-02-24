# Propuesta Técnica: Evolución a Sistema Multi-Agente (CrewAI + HuggingFace)

## 1. Objetivo
Evolucionar el sistema actual de investigación lineal hacia una arquitectura de **Agentes de IA especializados**. El objetivo es mejorar la calidad de los hallazgos, asegurar la coherencia de los usuarios sintéticos y profesionalizar el análisis final, manteniendo el control total sobre los datos y el alcance de la investigación.

## 2. Arquitectura de Agentes (Los 5 Roles)

Proponemos un equipo de 5 agentes con responsabilidades claramente delimitadas:

1.  **Orquestador (Process Manager):** Coordina el flujo de trabajo secuencial. Se asegura de que la salida de un agente sea la entrada correcta del siguiente y gestiona el estado de la investigación.
2.  **Entrevistador (Brief Specialist):** Analiza la descripción de la investigación (brief) y el producto. Su misión es extraer los puntos clave y las preguntas que se deben "hacer" a los usuarios, sin inventar contexto externo.
3.  **Respondedor (Synthetic User Persona):** "Encarna" al usuario sintético. Utiliza el perfil psicológico y las dimensiones (barreras, necesidades) para responder al cuestionario de forma realista y coherente.
4.  **Validador (Quality Control):** Actúa como filtro crítico. Revisa que las respuestas del Respondedor no sean genéricas, que no tengan alucinaciones y que respeten estrictamente el tono del arquetipo.
5.  **Analista (UX Researcher):** Recopila todas las respuestas validadas para generar el informe final de hallazgos, patrones y recomendaciones accionables.

## 3. Stack Tecnológico Propuesto

*   **Framework de Agentes:** `CrewAI` (Elegido por su rapidez de desarrollo y facilidad para definir roles/tareas).
*   **Motor de IA (LLM):** `HuggingFace API` (vía `HuggingFaceEndpoint` de LangChain) para total independencia de modelos locales u otros proveedores.
*   **Backend:** `FastAPI` (Manteniendo la estructura actual, pero refactorizando el `core`).
*   **Frontend:** `Streamlit` (Sin cambios necesarios para el usuario final).
*   **Persistencia:** Sistema de archivos JSON (`backend/storage/`) mejorado para trazabilidad por agente.

## 4. Flujo de Ejecución y Persistencia

La ejecución será **secuencial y determinista**, siguiendo estos pasos para garantizar que no se pierda información:

1.  **Ingesta:** Se guardan los datos de Producto e Investigación (JSON).
2.  **Fase de Preguntas:** El **Entrevistador** genera el guion basado en el brief.
3.  **Fase de Respuesta (Bucle por Usuario):**
    *   Se genera/recupera el perfil del usuario (JSON).
    *   El **Respondedor** genera sus respuestas.
    *   El **Validador** aprueba o solicita corrección.
    *   **Persistencia:** Se guardan las respuestas validadas por cada usuario (`usuarios/{id}/respuestas.json`).
4.  **Fase de Síntesis:** El **Analista** procesa todos los JSON de respuestas y genera el informe final (`resultados/analisis.json`).

## 5. Ventajas del Cambio

*   **Mayor Realismo:** Al separar al "Preguntador" del "Respondedor", eliminamos el sesgo de que el LLM se responda a sí mismo en un solo paso.
*   **Control de Calidad:** El agente Validador asegura que los textos sean correctos antes de que lleguen al analista.
*   **Trazabilidad Total:** Podremos auditar no solo el resultado final, sino el "pensamiento" y las respuestas individuales de cada agente en cada etapa.
*   **Escalabilidad:** Añadir nuevas capacidades (ej. un agente experto en accesibilidad) será tan sencillo como añadir un nuevo rol a la "Crew".

## 6. Plan de Implementación (Roadmap Rápido)

*   **Semana 1:** Setup de CrewAI con HuggingFace y definición de agentes/tareas en el backend.
*   **Semana 1-2:** Refactorización de la lógica de guardado para soportar el flujo multi-agente.
*   **Semana 2:** Pruebas de coherencia y ajuste de prompts de los agentes.

---

**Nota para el equipo:** Esta propuesta no requiere cambios en la interfaz de usuario, solo una actualización del "cerebro" del sistema para hacerlo más robusto y profesional.

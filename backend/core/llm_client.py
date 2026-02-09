"""
Cliente LLM para interactuar con diferentes proveedores de modelos de lenguaje
"""
import requests
import json
from typing import Optional, Dict, Any
import time
import random
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from config import LLAMA_CONFIG, ANYTHINGLLM_CONFIG


class LLMClient:
    """Cliente para interactuar con modelos de lenguaje"""
    
    def __init__(self, provider: str = "llama", config: Optional[Dict[str, Any]] = None):
        """
        Inicializa el cliente LLM
        
        Args:
            provider: "llama" o "chatgpt"
            config: Configuración personalizada del proveedor
        """
        self.provider = provider.lower()
        self.config = config or {}
        # Timestamp monotónico para throttling entre llamadas.
        self._last_request_ts: float = 0.0
        
        if self.provider == "llama":
            self._init_llama()
        elif self.provider == "chatgpt":
            self._init_chatgpt()
        else:
            raise ValueError(f"Proveedor no soportado: {provider}")
    
    def _init_llama(self):
        """
        Inicializa configuración para el proveedor "llama" legacy.

        Históricamente este proyecto usaba provider="llama" y luego un sub-proveedor
        en config["provider"] (p.ej. "ollama").

        Extendemos esto para soportar también "anythingllm".
        """
        llama_provider = (self.config.get("provider") or LLAMA_CONFIG["provider"] or "ollama").strip().lower()
        self.llama_provider = llama_provider
        
        if llama_provider == "ollama":
            self.base_url = self.config.get("base_url", LLAMA_CONFIG["base_url"])
            model_config = self.config.get("model", LLAMA_CONFIG["model"])
            self.min_delay_ms = int(self.config.get("min_delay_ms") or 0)
            
            # Solo intentamos detectar el modelo si no estamos en una operación de solo verificación
            # Para evitar llamadas dobles y timeouts innecesarios
            self.model = model_config
        elif llama_provider == "anythingllm":
            self.base_url = (self.config.get("base_url") or ANYTHINGLLM_CONFIG["base_url"]).strip()
            self.api_key = (self.config.get("api_key") or ANYTHINGLLM_CONFIG.get("api_key", "") or "").strip()
            self.workspace_slug = (self.config.get("workspace_slug") or ANYTHINGLLM_CONFIG.get("workspace_slug", "") or "").strip()
            self.mode = (self.config.get("mode") or ANYTHINGLLM_CONFIG.get("mode") or "query").strip().lower()
            self.min_delay_ms = int(self.config.get("min_delay_ms") or ANYTHINGLLM_CONFIG.get("min_delay_ms") or 0)
            self.max_retries = int(self.config.get("max_retries") or ANYTHINGLLM_CONFIG.get("max_retries") or 0)
        else:
            raise ValueError(f"Proveedor LLM no soportado: {llama_provider}")

    def _maybe_throttle(self) -> None:
        """
        Inserta una pausa mínima entre llamadas para evitar rate limits por ráfagas.
        """
        ms = int(getattr(self, "min_delay_ms", 0) or 0)
        if ms <= 0:
            return
        now = time.monotonic()
        elapsed = now - float(getattr(self, "_last_request_ts", 0.0) or 0.0)
        wait_s = (ms / 1000.0) - elapsed
        if wait_s > 0:
            time.sleep(wait_s)
        self._last_request_ts = time.monotonic()
    
    def _get_available_model(self, preferred_model: str) -> str:
        """Intenta obtener el modelo preferido o el primero disponible"""
        try:
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            models_data = response.json()
            available_models = [model.get("name", "") for model in models_data.get("models", [])]
            
            if available_models:
                # Si el modelo preferido está disponible, usarlo
                if preferred_model in available_models:
                    return preferred_model
                # Si no, usar el primero disponible
                return available_models[0]
            # Si no hay modelos, devolver el preferido
            return preferred_model
        except:
            # Si falla, devolver el preferido
            return preferred_model
    
    def _init_chatgpt(self):
        """Inicializa configuración para ChatGPT (preparado para futuro)"""
        # TODO: Implementar cuando se necesite ChatGPT
        pass
    
    def generate(self, prompt: str, temperature: Optional[float] = None, 
                 max_tokens: Optional[int] = None, **kwargs) -> str:
        """
        Genera texto usando el modelo de lenguaje
        
        Args:
            prompt: El prompt a enviar al modelo
            temperature: Temperatura para la generación (opcional)
            max_tokens: Máximo número de tokens (opcional)
            **kwargs: Argumentos adicionales específicos del proveedor
        
        Returns:
            Respuesta del modelo como string
        """
        # Throttling global por instancia (aplica a cualquier proveedor).
        self._maybe_throttle()
        if self.provider == "llama":
            if getattr(self, "llama_provider", "ollama") == "anythingllm":
                return self._generate_anythingllm(prompt, **kwargs)
            return self._generate_llama(prompt, temperature, max_tokens, **kwargs)
        elif self.provider == "chatgpt":
            return self._generate_chatgpt(prompt, temperature, max_tokens, **kwargs)
    
    def _generate_llama(self, prompt: str, temperature: Optional[float] = None,
                       max_tokens: Optional[int] = None, **kwargs) -> str:
        """Genera texto usando LLaMA vía Ollama"""
        # Usar valores por defecto si no se proporcionan
        temp = temperature if temperature is not None else self.config.get("temperature", LLAMA_CONFIG["temperature"])
        max_tok = max_tokens if max_tokens is not None else self.config.get("max_tokens", LLAMA_CONFIG["max_tokens"])
        
        # Preparar request para Ollama
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temp,
                "num_predict": max_tok
            }
        }
        
        try:
            response = requests.post(url, json=payload, timeout=300)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error al generar con LLaMA: {str(e)}")

    def _anythingllm_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        token = (getattr(self, "api_key", "") or "").strip()
        if token:
            # AnythingLLM puede aceptar:
            # - Authorization: Bearer <API_KEY>
            # - X-API-Key / X-API-KEY: <API_KEY>
            # Enviamos ambos para maximizar compatibilidad.
            if token.lower().startswith("bearer "):
                bearer = token
                raw = token.split(" ", 1)[1].strip() if " " in token else token
            else:
                bearer = f"Bearer {token}"
                raw = token

            headers["Authorization"] = bearer
            headers["X-API-Key"] = raw
            headers["X-API-KEY"] = raw
        return headers

    def _anythingllm_base_variants(self) -> list[str]:
        """
        Normaliza base_url para probar variantes comunes.
        Ej:
          - http://host:3001
          - http://host:3001/api
        """
        base = (getattr(self, "base_url", "") or "").strip().rstrip("/")
        if not base:
            return []
        variants = [base]
        if base.endswith("/api"):
            variants.append(base[:-4])
        return list(dict.fromkeys([v.rstrip("/") for v in variants if v]))

    def _anythingllm_chat_urls(self) -> list[str]:
        slug = (getattr(self, "workspace_slug", "") or "").strip()
        urls: list[str] = []
        for base in self._anythingllm_base_variants():
            # Endpoints validados en AnythingLLM (Desktop/self-hosted):
            # - /api/v1/workspace/{slug}/chat
            # También se ha visto /v1/workspace/{slug}/chat en algunas variantes.
            urls.extend([
                f"{base}/api/v1/workspace/{slug}/chat",
                f"{base}/v1/workspace/{slug}/chat",
            ])
        return list(dict.fromkeys(urls))

    def _resolve_anythingllm_workspace_slug(self, force: bool = False) -> Optional[str]:
        """
        Resuelve un workspace slug para AnythingLLM.

        - Si ya viene configurado, se usa tal cual.
        - Si está vacío, intentamos autodetectar el primer workspace vía API.
          (Requiere normalmente API key con permisos suficientes.)
        """
        slug = (getattr(self, "workspace_slug", "") or "").strip()

        for base in self._anythingllm_base_variants():
            candidate_urls = [
                f"{base}/api/v1/workspaces",
                f"{base}/v1/workspaces",
                f"{base}/api/v1/workspace",
                f"{base}/v1/workspace",
                f"{base}/api/workspaces",
                f"{base}/api/workspace",
            ]

            for url in candidate_urls:
                try:
                    resp = requests.get(url, headers=self._anythingllm_headers(), timeout=8)
                    if resp.status_code == 404:
                        continue
                    resp.raise_for_status()
                    data = resp.json() if resp.content else None

                    # Formatos típicos: { "workspaces": [ { "slug": "..." }, ... ] } o lista directa
                    workspaces = None
                    if isinstance(data, dict):
                        if isinstance(data.get("workspaces"), list):
                            workspaces = data.get("workspaces")
                        elif isinstance(data.get("data"), list):
                            workspaces = data.get("data")
                    elif isinstance(data, list):
                        workspaces = data

                    if not isinstance(workspaces, list) or not workspaces:
                        continue

                    # Si hay un slug configurado, intentamos validar/normalizar:
                    # - Si coincide con un slug, lo mantenemos
                    # - Si coincide con el nombre, lo convertimos al slug correcto
                    wanted = slug.strip().lower() if slug else None

                    for ws in workspaces:
                        if not isinstance(ws, dict):
                            continue
                        s = ws.get("slug") or ws.get("workspaceSlug") or ws.get("workspace_slug")
                        name = ws.get("name")

                        s_norm = s.strip() if isinstance(s, str) else ""
                        name_norm = name.strip() if isinstance(name, str) else ""

                        if wanted and (s_norm.lower() == wanted or name_norm.lower() == wanted):
                            # Normalizar a slug real
                            if s_norm:
                                self.workspace_slug = s_norm
                                return self.workspace_slug

                    # Si venimos forzando o no hay slug configurado, elegimos el primero disponible
                    if force or not slug:
                        for ws in workspaces:
                            if not isinstance(ws, dict):
                                continue
                            s = ws.get("slug") or ws.get("workspaceSlug") or ws.get("workspace_slug")
                            if isinstance(s, str) and s.strip():
                                self.workspace_slug = s.strip()
                                return self.workspace_slug
                except Exception:
                    continue

        # Si no pudimos validar pero había uno configurado, devolvemos el que haya (mejor que None)
        if slug and not force:
            return slug
        return None

    def _generate_anythingllm(self, prompt: str, **kwargs) -> str:
        """
        Genera texto usando AnythingLLM.

        Endpoint esperado (según issue/documentación de la comunidad):
        - POST /v1/workspace/{slug}/chat
          body: {"message": "...", "mode": "query"|"chat"}
        """
        if not getattr(self, "base_url", None):
            raise Exception("AnythingLLM: falta base_url")
        slug = self._resolve_anythingllm_workspace_slug()
        if not slug:
            raise Exception(
                "AnythingLLM: falta workspace_slug. "
                "Puedes (a) indicarlo en la UI, o (b) definir ANYTHINGLLM_WORKSPACE_SLUG en el backend, "
                "o (c) permitir que la API liste workspaces (requiere API key con permisos)."
            )

        mode = (getattr(self, "mode", "query") or "query").strip().lower()
        if mode not in {"query", "chat"}:
            mode = "query"

        def _is_no_relevant_info(text: Optional[str]) -> bool:
            if not text:
                return False
            t = str(text).strip().lower()
            needles = [
                "there is no relevant information in this workspace",
                "no relevant information in this workspace",
                "no relevant information",
            ]
            return any(n in t for n in needles)

        def _payload(_mode: str) -> dict:
            return {"message": prompt, "mode": _mode}

        def _is_rate_limit_error(err: Optional[Exception]) -> bool:
            if not err:
                return False
            msg = str(err).lower()
            return ("429" in msg) or ("too many requests" in msg) or ("rate limit" in msg) or ("ratelimit" in msg)

        def _try_chat_once() -> tuple[Optional[str], Optional[Exception], bool]:
            last_err: Optional[Exception] = None
            any_404 = False
            for url in self._anythingllm_chat_urls():
                try:
                    response = requests.post(url, headers=self._anythingllm_headers(), json=_payload(mode), timeout=300)
                    # 404: puede ser path incorrecto o slug incorrecto
                    if response.status_code == 404:
                        any_404 = True
                        # No machacar un error previo más informativo (p.ej. abort/quota)
                        if last_err is None:
                            last_err = Exception(f"AnythingLLM endpoint no encontrado en {url} (404)")
                        continue
                    # Muchísimas instalaciones de AnythingLLM devuelven errores del proveedor como:
                    # HTTP 500 con body JSON { type: "abort", error: "429 ... quota ..." }.
                    # Por eso intentamos parsear JSON ANTES de raise_for_status.
                    data = None
                    try:
                        if response.content:
                            data = response.json()
                    except Exception:
                        data = None

                    if isinstance(data, dict) and data.get("type") == "abort" and isinstance(data.get("error"), str):
                        return None, Exception(f"AnythingLLM abort: {data.get('error')}"), any_404

                    if response.status_code == 429:
                        return None, Exception("AnythingLLM rate limit (429): Too Many Requests"), any_404
                    response.raise_for_status()
                    # Algunas rutas pueden devolver texto/stream aunque sea 200.
                    # Intentamos JSON primero; si falla, tratamos de parsear una línea "data: {...}".
                    try:
                        data = data if isinstance(data, (dict, list)) else (response.json() if response.content else {})
                    except Exception:
                        raw_text = (response.text or "").strip()
                        if raw_text.startswith("data:"):
                            first = raw_text.splitlines()[0]
                            maybe_json = first.replace("data:", "", 1).strip()
                            try:
                                data = json.loads(maybe_json)
                            except Exception:
                                data = {"text": raw_text}
                        else:
                            data = {"text": raw_text}

                    # Respuesta típica: incluye texto generado por LLM y sources.
                    # No dependemos de un esquema exacto: buscamos campos comunes.
                    for key in ["textResponse", "response", "message", "answer", "text"]:
                        val = data.get(key) if isinstance(data, dict) else None
                        if isinstance(val, str) and val.strip():
                            return val, None, any_404

                    # Algunos formatos devuelven { "data": { "textResponse": ... } }
                    if isinstance(data, dict) and isinstance(data.get("data"), dict):
                        inner = data["data"]
                        for key in ["textResponse", "response", "message", "answer", "text"]:
                            val = inner.get(key)
                            if isinstance(val, str) and val.strip():
                                return val, None, any_404

                    # Fallback: serializar
                    return json.dumps(data, ensure_ascii=False), None, any_404
                except requests.exceptions.HTTPError as e:
                    last_err = e
                    # Mensaje más útil para auth
                    if response is not None and response.status_code in (401, 403):
                        return None, Exception("AnythingLLM: no autorizado (revisa API key y permisos)"), any_404
                    if response is not None and response.status_code == 429:
                        return None, Exception("AnythingLLM rate limit (429): Too Many Requests"), any_404
                except requests.exceptions.RequestException as e:
                    last_err = e
                    continue
            return None, last_err, any_404

        # 1) Intento con slug actual (con reintentos en rate limit)
        retries = int(getattr(self, "max_retries", 0) or 0)
        text: Optional[str] = None
        err: Optional[Exception] = None
        any_404 = False
        for attempt in range(retries + 1):
            text, err, any_404 = _try_chat_once()
            if text is not None:
                break
            if _is_rate_limit_error(err) and attempt < retries:
                # Backoff exponencial con jitter pequeño.
                sleep_s = min(8.0, (0.6 * (2 ** attempt)) + random.random() * 0.2)
                time.sleep(sleep_s)
                continue
            break

        if text is not None:
            # Fallback: si estamos en query y el workspace no tiene chunks relevantes,
            # reintentamos en modo chat para que responda el LLM igualmente.
            if mode == "query" and _is_no_relevant_info(text):
                mode = "chat"
                # Reintentar con el mismo esquema (incluye rate-limit retries)
                text2 = None
                err2: Optional[Exception] = None
                any_404_2 = False
                for attempt in range(retries + 1):
                    text2, err2, any_404_2 = _try_chat_once()
                    if text2 is not None:
                        break
                    if _is_rate_limit_error(err2) and attempt < retries:
                        sleep_s = min(8.0, (0.6 * (2 ** attempt)) + random.random() * 0.2)
                        time.sleep(sleep_s)
                        continue
                    break
                if text2 is not None:
                    return text2
                err = err2 or err
                any_404 = any_404 or any_404_2
                # si falló el fallback, devolvemos el mensaje original (más informativo para el usuario)
                return text
            return text

        # 2) Si dio 404, puede ser slug incorrecto: intentamos autodetectar y reintentar
        if any_404:
            resolved = self._resolve_anythingllm_workspace_slug(force=True)
            if resolved:
                text2 = None
                err2: Optional[Exception] = None
                for attempt in range(retries + 1):
                    text2, err2, _ = _try_chat_once()
                    if text2 is not None:
                        break
                    if _is_rate_limit_error(err2) and attempt < retries:
                        sleep_s = min(8.0, (0.6 * (2 ** attempt)) + random.random() * 0.2)
                        time.sleep(sleep_s)
                        continue
                    break
                if text2 is not None:
                    if mode == "query" and _is_no_relevant_info(text2):
                        mode = "chat"
                        text3 = None
                        err3: Optional[Exception] = None
                        for attempt in range(retries + 1):
                            text3, err3, _ = _try_chat_once()
                            if text3 is not None:
                                break
                            if _is_rate_limit_error(err3) and attempt < retries:
                                sleep_s = min(8.0, (0.6 * (2 ** attempt)) + random.random() * 0.2)
                                time.sleep(sleep_s)
                                continue
                            break
                        if text3 is not None:
                            return text3
                        err2 = err3 or err2
                    return text2
                err = err2 or err

        raise Exception(f"Error al generar con AnythingLLM: {err}")
    
    def _generate_chatgpt(self, prompt: str, temperature: Optional[float] = None,
                        max_tokens: Optional[int] = None, **kwargs) -> str:
        """Genera texto usando ChatGPT (preparado para futuro)"""
        # TODO: Implementar cuando se necesite ChatGPT
        raise NotImplementedError("ChatGPT aún no está implementado")
    
    def set_config(self, **kwargs):
        """Actualiza la configuración del cliente"""
        self.config.update(kwargs)
        if self.provider == "llama":
            self._init_llama()
    
    def check_connection(self) -> Dict[str, Any]:
        """
        Verifica la conexión con el proveedor LLM
        
        Returns:
            Diccionario con status y detalles de la conexión
        """
        if self.provider == "llama":
            if getattr(self, "llama_provider", "ollama") == "anythingllm":
                return self._check_anythingllm_connection()
            return self._check_ollama_connection()
        elif self.provider == "chatgpt":
            return {"status": "not_implemented", "message": "ChatGPT no implementado"}
        else:
            return {"status": "error", "message": f"Proveedor desconocido: {self.provider}"}
    
    def _check_ollama_connection(self) -> Dict[str, Any]:
        """Verifica la conexión con Ollama"""
        try:
            # Intentar listar modelos disponibles
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            models_data = response.json()
            models = [model.get("name", "") for model in models_data.get("models", [])]
            
            # Verificar si el modelo configurado está disponible
            model_available = self.model in models if models else False
            
            return {
                "status": "connected",
                "base_url": self.base_url,
                "model": self.model,
                "model_available": model_available,
                "available_models": models,
                "message": f"Conectado a Ollama. Modelo '{self.model}' {'disponible' if model_available else 'no encontrado'}"
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "disconnected",
                "base_url": self.base_url,
                "model": self.model,
                "message": f"No se pudo conectar a Ollama en {self.base_url}. Verifica que Ollama esté corriendo."
            }
        except requests.exceptions.Timeout:
            return {
                "status": "timeout",
                "base_url": self.base_url,
                "model": self.model,
                "message": f"Timeout al conectar con Ollama en {self.base_url}"
            }
        except Exception as e:
            return {
                "status": "error",
                "base_url": self.base_url,
                "model": self.model,
                "message": f"Error al verificar conexión: {str(e)}"
            }

    def _check_anythingllm_connection(self) -> Dict[str, Any]:
        """
        Verifica conectividad básica con AnythingLLM.

        La doc oficial indica que la instancia expone un swagger en /api/docs.
        Esto no valida credenciales ni workspace, pero confirma reachability.
        """
        base = (getattr(self, "base_url", "") or "").rstrip("/")
        slug = (getattr(self, "workspace_slug", "") or "").strip()
        try:
            url = f"{base}/api/docs"
            resp = requests.get(url, timeout=5)
            if resp.status_code >= 500:
                return {
                    "status": "error",
                    "provider": "anythingllm",
                    "base_url": base,
                    "workspace_slug": slug or None,
                    "message": f"AnythingLLM respondió {resp.status_code} en /api/docs",
                }
            # 200/301/302/401/403 son señales de reachability
            reachable = resp.status_code in {200, 301, 302, 401, 403}
            return {
                "status": "connected" if reachable else "disconnected",
                "provider": "anythingllm",
                "base_url": base,
                "workspace_slug": slug or None,
                "message": "AnythingLLM accesible" if reachable else f"AnythingLLM no accesible (HTTP {resp.status_code})",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "disconnected",
                "provider": "anythingllm",
                "base_url": base,
                "workspace_slug": slug or None,
                "message": f"No se pudo conectar a AnythingLLM en {base}.",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "timeout",
                "provider": "anythingllm",
                "base_url": base,
                "workspace_slug": slug or None,
                "message": f"Timeout al conectar con AnythingLLM en {base}.",
            }
        except Exception as e:
            return {
                "status": "error",
                "provider": "anythingllm",
                "base_url": base,
                "workspace_slug": slug or None,
                "message": f"Error al verificar AnythingLLM: {str(e)}",
            }

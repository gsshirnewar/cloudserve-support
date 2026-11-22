"""LLM provider abstraction with caching, resilience, and typed degraded results (T15)."""

from __future__ import annotations

import hashlib
import json
import random
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from src.config import AppConfig, get_config
from src.logging_config import get_logger

logger = get_logger(__name__)


class ProviderError(Exception):
    """Base provider exception (internal)."""


class ProviderTimeoutError(ProviderError):
    pass


class ProviderRateLimitError(ProviderError):
    def __init__(self, message: str = "rate limited", retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class ProviderServerError(ProviderError):
    pass


class ProviderUnavailableError(ProviderError):
    pass


@dataclass
class LLMRequest:
    prompt: Union[str, Sequence[Dict[str, Any]]]
    model: Optional[str] = None
    prompt_version: str = "unversioned"
    params: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResult:
    ok: bool
    text: Optional[str] = None
    parsed: Any = None
    raw: Any = None
    degraded: bool = False
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    retries: int = 0
    latency_ms: float = 0.0
    cache_hit: bool = False
    model: Optional[str] = None
    provider: Optional[str] = None
    prompt_version: Optional[str] = None
    simulation_mode: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def build_cache_key(request: LLMRequest, provider_name: str, model: str) -> str:
    payload = {
        "provider": provider_name,
        "model": model,
        "prompt": request.prompt,
        "prompt_version": request.prompt_version,
        "params": request.params or {},
    }
    digest = hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()
    return digest


class DiskCache:
    def __init__(self, cache_dir: Path, enabled: bool = True):
        self.cache_dir = cache_dir
        self.enabled = enabled
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path_for(self, key: str) -> Path:
        subdir = self.cache_dir / "llm"
        subdir.mkdir(parents=True, exist_ok=True)
        return subdir / f"{key}.json"

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
        path = self._path_for(key)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def set(self, key: str, value: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        path = self._path_for(key)
        tmp = path.with_suffix(".tmp")
        try:
            with self._lock:
                with tmp.open("w", encoding="utf-8") as f:
                    json.dump(value, f, ensure_ascii=False, default=str)
                tmp.replace(path)
        except Exception:
            # Cache failures must not break pipeline.
            try:
                if tmp.exists():
                    tmp.unlink()
            except Exception:
                pass


class RateLimiter:
    """Simple concurrency + spacing limiter for free-tier safety."""

    def __init__(self, max_concurrency: int = 4, min_interval_seconds: float = 0.0):
        self.max_concurrency = max(1, int(max_concurrency))
        self.min_interval_seconds = max(0.0, float(min_interval_seconds))
        self._semaphore = threading.Semaphore(self.max_concurrency)
        self._lock = threading.Lock()
        self._last_call_monotonic = 0.0

    def acquire(self) -> None:
        self._semaphore.acquire()
        if self.min_interval_seconds > 0:
            with self._lock:
                now = time.monotonic()
                wait_for = self.min_interval_seconds - (now - self._last_call_monotonic)
                if wait_for > 0:
                    time.sleep(wait_for)
                self._last_call_monotonic = time.monotonic()

    def release(self) -> None:
        try:
            self._semaphore.release()
        except Exception:
            pass


def _extract_text(response: Any) -> str:
    if response is None:
        return ""
    if isinstance(response, str):
        return response
    # LangChain AIMessage-like
    content = getattr(response, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(str(item.get("text", "")))
        if parts:
            return "".join(parts)
    # OpenAI-like choices
    choices = getattr(response, "choices", None)
    if choices and isinstance(choices, list):
        try:
            msg = choices[0].message
            txt = getattr(msg, "content", None)
            if isinstance(txt, str):
                return txt
        except Exception:
            pass
    if isinstance(response, dict):
        if "text" in response:
            return str(response["text"])
        if "content" in response:
            return str(response["content"])
    return str(response)


def _default_structured_parse(text: str) -> Any:
    text = (text or "").strip()
    if not text:
        raise ValueError("empty response")
    # Try direct JSON first.
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try fenced/embedded JSON object.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        return json.loads(candidate)
    raise ValueError("response is not parseable JSON")


class ProviderBackend:
    name: str = "base"

    def generate(self, request: LLMRequest, model: str, timeout_seconds: float) -> Any:
        raise NotImplementedError


class SimulationBackend(ProviderBackend):
    name = "simulation"

    def __init__(self, mode: str = "off", success_text: str = '{"status":"ok"}'):
        self.mode = (mode or "off").lower()
        self.success_text = success_text
        self.call_count = 0
        self._lock = threading.Lock()
        self._rate_limit_failures_remaining = 1  # for 429-then-succeed

    def generate(self, request: LLMRequest, model: str, timeout_seconds: float) -> Any:
        with self._lock:
            self.call_count += 1
            mode = self.mode
            failures_remaining = self._rate_limit_failures_remaining
        # Normalize aliases.
        if mode in {"provider_down", "outage"}:
            mode = "unavailable"
        if mode in {"5xx"}:
            mode = "server_error"
        if mode in {"429"}:
            mode = "rate_limit"

        if mode == "timeout":
            raise ProviderTimeoutError("simulated timeout")
        if mode == "unavailable":
            raise ProviderUnavailableError("simulated provider unavailable")
        if mode == "server_error":
            raise ProviderServerError("simulated server error")
        if mode == "rate_limit":
            with self._lock:
                if self._rate_limit_failures_remaining > 0:
                    self._rate_limit_failures_remaining -= 1
                    raise ProviderRateLimitError("simulated 429 rate limit")
            return self.success_text
        # off/success
        return self.success_text


class LangChainOpenAICompatibleBackend(ProviderBackend):
    name = "langchain_openai_compatible"

    def __init__(self, config: AppConfig):
        self.config = config

    def _client_for(self, model: str, timeout_seconds: float):
        provider = self.config.provider.llm_provider.lower()
        try:
            from langchain_openai import ChatOpenAI  # type: ignore
        except Exception as e:  # pragma: no cover - depends on env
            raise ProviderUnavailableError(f"langchain_openai unavailable: {e}") from e

        temperature = float(self.config.models.llm_temperature)
        if provider == "openrouter":
            api_key = self.config.provider.openrouter_api_key
            if not api_key:
                raise ProviderUnavailableError("OPENROUTER_API_KEY is not configured")
            return ChatOpenAI(
                model=model,
                api_key=api_key,
                base_url=self.config.provider.openrouter_base_url,
                temperature=temperature,
                timeout=timeout_seconds,
                max_retries=0,
            )
        if provider == "groq":
            api_key = self.config.provider.groq_api_key
            if not api_key:
                raise ProviderUnavailableError("GROQ_API_KEY is not configured")
            # Groq OpenAI-compatible endpoint
            base_url = "https://api.groq.com/openai/v1"
            return ChatOpenAI(
                model=model,
                api_key=api_key,
                base_url=base_url,
                temperature=temperature,
                timeout=timeout_seconds,
                max_retries=0,
            )
        raise ProviderUnavailableError(f"Unsupported llm_provider: {provider}")

    def generate(self, request: LLMRequest, model: str, timeout_seconds: float) -> Any:
        client = self._client_for(model=model, timeout_seconds=timeout_seconds)
        prompt = request.prompt
        try:
            # Accept plain text or chat-like message structures.
            if isinstance(prompt, str):
                return client.invoke(prompt)
            # LangChain chat models accept list-of-messages or list-of-tuples in many versions.
            return client.invoke(prompt)  # type: ignore[arg-type]
        except Exception as e:
            msg = str(e).lower()
            status = getattr(e, "status_code", None) or getattr(e, "http_status", None)
            if "timeout" in msg or "timed out" in msg:
                raise ProviderTimeoutError(str(e)) from e
            if status == 429 or "429" in msg or "rate limit" in msg:
                raise ProviderRateLimitError(str(e)) from e
            if status and int(status) >= 500:
                raise ProviderServerError(str(e)) from e
            if "unavailable" in msg or "connection" in msg or "api key" in msg:
                raise ProviderUnavailableError(str(e)) from e
            raise ProviderError(str(e)) from e


class LLMProvider:
    def __init__(
        self,
        config: Optional[AppConfig] = None,
        backend: Optional[ProviderBackend] = None,
        cache: Optional[DiskCache] = None,
        rate_limiter: Optional[RateLimiter] = None,
        simulation_mode: Optional[str] = None,
    ):
        self.config = config or get_config()
        self.simulation_mode = (simulation_mode or self.config.runtime.provider_simulation_mode or "off").lower()
        self.cache = cache or DiskCache(
            cache_dir=self.config.paths.cache_dir,
            enabled=bool(self.config.runtime.enable_cache),
        )
        self.rate_limiter = rate_limiter or RateLimiter(max_concurrency=self.config.runtime.max_concurrency)
        if backend is not None:
            self.backend = backend
        elif self.simulation_mode != "off":
            self.backend = SimulationBackend(mode=self.simulation_mode)
        else:
            self.backend = LangChainOpenAICompatibleBackend(self.config)
        self.provider_name = self.config.provider.llm_provider

    def _resolve_model(self, request: LLMRequest) -> str:
        if request.model:
            return request.model
        if self.provider_name == "groq":
            return self.config.provider.groq_model
        return self.config.provider.openrouter_model

    def generate(
        self,
        request: LLMRequest,
        *,
        expect_json: bool = False,
        parser: Optional[Callable[[str], Any]] = None,
        parse_retries: int = 1,
        cache_enabled: Optional[bool] = None,
        simulation_mode: Optional[str] = None,
    ) -> LLMResult:
        """Generate a response with retries/cache/rate limiting and typed degraded fallback."""
        start = time.monotonic()
        retries = 0
        model = self._resolve_model(request)
        timeout_seconds = float(request.timeout_seconds or self.config.provider.request_timeout_seconds)
        max_retries = max(0, int(self.config.provider.max_retries))
        use_cache = self.cache.enabled if cache_enabled is None else bool(cache_enabled)
        cache_key = build_cache_key(request, self.provider_name, model)

        # Runtime simulation override (uses simulation backend behavior without mutating global config).
        backend = self.backend
        effective_sim_mode = self.simulation_mode
        if simulation_mode is not None and simulation_mode.lower() != self.simulation_mode:
            backend = SimulationBackend(mode=simulation_mode.lower())
            effective_sim_mode = simulation_mode.lower()

        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return LLMResult(
                    ok=bool(cached.get("ok", True)),
                    text=cached.get("text"),
                    parsed=cached.get("parsed"),
                    raw=cached.get("raw"),
                    degraded=bool(cached.get("degraded", False)),
                    error_type=cached.get("error_type"),
                    error_message=cached.get("error_message"),
                    retries=int(cached.get("retries", 0)),
                    latency_ms=0.0,
                    cache_hit=True,
                    model=model,
                    provider=self.provider_name,
                    prompt_version=request.prompt_version,
                    simulation_mode=effective_sim_mode,
                )

        parse_attempts = 0
        max_parse_attempts = 1 + max(0, int(parse_retries))
        try:
            while True:
                try:
                    self.rate_limiter.acquire()
                    try:
                        raw = self._call_with_retries(backend, request, model, timeout_seconds, max_retries)
                        retries = int(getattr(raw, "_provider_retries", 0)) if not isinstance(raw, dict) else 0
                    finally:
                        self.rate_limiter.release()

                    # _call_with_retries returns tuple(raw_response, retries_count)
                    if isinstance(raw, tuple) and len(raw) == 2:
                        raw_response, retries = raw
                    else:
                        raw_response, retries = raw, 0

                    text = _extract_text(raw_response)
                    parsed: Any = None
                    if expect_json or parser is not None:
                        while True:
                            try:
                                parse_fn = parser or _default_structured_parse
                                parsed = parse_fn(text)
                                break
                            except Exception as pe:
                                parse_attempts += 1
                                if parse_attempts >= max_parse_attempts:
                                    raise ValueError(f"structured output parse failed: {pe}") from pe
                                # Retry generation once/more for parse failures.
                                self.rate_limiter.acquire()
                                try:
                                    raw_response, gen_retries = self._call_with_retries(
                                        backend, request, model, timeout_seconds, max_retries
                                    )
                                    retries += gen_retries
                                finally:
                                    self.rate_limiter.release()
                                text = _extract_text(raw_response)

                    latency_ms = (time.monotonic() - start) * 1000.0
                    result = LLMResult(
                        ok=True,
                        text=text,
                        parsed=parsed,
                        raw=_safe_raw(raw_response),
                        degraded=False,
                        retries=retries,
                        latency_ms=latency_ms,
                        cache_hit=False,
                        model=model,
                        provider=self.provider_name,
                        prompt_version=request.prompt_version,
                        simulation_mode=effective_sim_mode,
                    )
                    if use_cache and result.ok:
                        self.cache.set(cache_key, _cacheable_result(result))
                    return result

                except ProviderRateLimitError as e:
                    # Should normally be handled inside retry loop, but degrade safely if exhausted.
                    return self._degraded("rate_limit", str(e), retries=retries, start=start, model=model, request=request, sim=effective_sim_mode)
                except ProviderTimeoutError as e:
                    return self._degraded("timeout", str(e), retries=retries, start=start, model=model, request=request, sim=effective_sim_mode)
                except ProviderServerError as e:
                    return self._degraded("server_error", str(e), retries=retries, start=start, model=model, request=request, sim=effective_sim_mode)
                except ProviderUnavailableError as e:
                    return self._degraded("unavailable", str(e), retries=retries, start=start, model=model, request=request, sim=effective_sim_mode)
                except ValueError as e:
                    # Parse failure after retries -> degraded typed result
                    return self._degraded("parse_error", str(e), retries=retries, start=start, model=model, request=request, sim=effective_sim_mode)
                except Exception as e:
                    return self._degraded("provider_error", str(e), retries=retries, start=start, model=model, request=request, sim=effective_sim_mode)
        except Exception as e:
            # Absolute safety net: never raise to pipeline.
            return self._degraded("unexpected_error", str(e), retries=retries, start=start, model=model, request=request, sim=effective_sim_mode)

    def _call_with_retries(
        self,
        backend: ProviderBackend,
        request: LLMRequest,
        model: str,
        timeout_seconds: float,
        max_retries: int,
    ) -> Tuple[Any, int]:
        attempt = 0
        while True:
            try:
                response = backend.generate(request=request, model=model, timeout_seconds=timeout_seconds)
                return response, attempt
            except (ProviderRateLimitError, ProviderServerError, ProviderTimeoutError) as e:
                if attempt >= max_retries:
                    raise
                delay = self._backoff_delay(attempt, e)
                logger.warning(
                    "LLM call failed; retrying",
                    extra={
                        "component": "llm.provider",
                        "event": "retry",
                        "outcome": type(e).__name__,
                    },
                )
                time.sleep(delay)
                attempt += 1
            except ProviderUnavailableError:
                # Outage/unavailable is typically not transient within short window; degrade promptly.
                raise
            except ProviderError:
                if attempt >= max_retries:
                    raise
                delay = self._backoff_delay(attempt, None)
                time.sleep(delay)
                attempt += 1

    @staticmethod
    def _backoff_delay(attempt: int, error: Optional[Exception]) -> float:
        base = 0.1 * (2 ** attempt)
        cap = 2.0
        retry_after = getattr(error, "retry_after", None) if error is not None else None
        if isinstance(retry_after, (int, float)) and retry_after > 0:
            base = max(base, float(retry_after))
        jitter = random.uniform(0.0, 0.1 * (2 ** attempt))
        return min(cap, base + jitter)

    def _degraded(
        self,
        error_type: str,
        message: str,
        retries: int,
        start: float,
        model: Optional[str],
        request: LLMRequest,
        sim: Optional[str],
    ) -> LLMResult:
        latency_ms = (time.monotonic() - start) * 1000.0
        logger.warning(
            "LLM provider degraded result",
            extra={"component": "llm.provider", "event": "degraded", "outcome": error_type},
        )
        return LLMResult(
            ok=False,
            degraded=True,
            error_type=error_type,
            error_message=message,
            retries=retries,
            latency_ms=latency_ms,
            cache_hit=False,
            model=model,
            provider=self.provider_name,
            prompt_version=request.prompt_version,
            simulation_mode=sim,
        )


def _safe_raw(raw: Any) -> Any:
    if raw is None or isinstance(raw, (str, int, float, bool, list, dict)):
        return raw
    # Best-effort serialization for common SDK objects.
    for attr in ("model_dump", "dict", "to_dict"):
        fn = getattr(raw, attr, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                pass
    if hasattr(raw, "content"):
        try:
            return {"content": getattr(raw, "content")}
        except Exception:
            pass
    return {"repr": repr(raw)[:1000]}


def _cacheable_result(result: LLMResult) -> Dict[str, Any]:
    # Store only deterministic/useful fields; never secrets.
    return {
        "ok": result.ok,
        "text": result.text,
        "parsed": result.parsed,
        "raw": result.raw,
        "degraded": result.degraded,
        "error_type": result.error_type,
        "error_message": result.error_message,
        "retries": result.retries,
        "model": result.model,
        "provider": result.provider,
        "prompt_version": result.prompt_version,
    }

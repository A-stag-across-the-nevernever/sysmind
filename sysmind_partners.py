"""LLM partner abstraction for sysmind — local or API. Stdlib only.

Ported from creature's LLMPartner protocol
(Sources/CreatureSpine/Sync/LLMPartner.swift): "Strings in, strings out.
No vendor-specific types."

A *slot* is a role (conscious / unconscious). A *partner* is whatever answers
for that slot — a local runtime or a remote endpoint. Nothing above this layer
knows which, so Ollama is one option rather than the substrate.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, Optional


class PartnerRole(str, Enum):
    """The two cognitive slots. Roles are discovered by calibration, not declared."""
    CONSCIOUS = "conscious"      # reasoning, explanation, the user's language
    UNCONSCIOUS = "unconscious"  # shell, configs, the machine's language


class PartnerError(RuntimeError):
    """A partner could not be reached or returned an unusable response."""


@dataclass
class PartnerMetadata:
    name: str
    provider: str      # "ollama" | "openai-compat" | ...
    model: str
    is_local: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LLMPartner(ABC):
    """Strings in, strings out."""

    @property
    @abstractmethod
    def metadata(self) -> PartnerMetadata:
        ...

    @abstractmethod
    def complete(self, prompt: str, system: Optional[str] = None,
                 timeout: float = 60.0) -> str:
        """Return the completion text. Raise PartnerError on failure."""

    def timed_complete(self, prompt: str, system: Optional[str] = None,
                       timeout: float = 60.0) -> "tuple[str, float]":
        """complete(), plus wall-clock latency in milliseconds."""
        start = time.monotonic()
        text = self.complete(prompt, system=system, timeout=timeout)
        return text, (time.monotonic() - start) * 1000.0


def _post_json(url: str, payload: Dict[str, Any], timeout: float,
               headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        raise PartnerError("HTTP {} from {}: {}".format(e.code, url, detail)) from e
    except urllib.error.URLError as e:
        raise PartnerError("cannot reach {}: {}".format(url, e.reason)) from e
    except json.JSONDecodeError as e:
        raise PartnerError("non-JSON response from {}".format(url)) from e


class OllamaPartner(LLMPartner):
    """Local Ollama over its HTTP API.

    Uses /api/generate rather than shelling out to `ollama run` — structured,
    supports a real system prompt, honours timeouts, and never touches a shell.
    """

    def __init__(self, model: str, host: str = "http://127.0.0.1:11434",
                 keep_alive: Optional[str] = None):
        self.model = model
        self.host = host.rstrip("/")
        self.keep_alive = keep_alive

    @property
    def metadata(self) -> PartnerMetadata:
        return PartnerMetadata(name=self.model, provider="ollama",
                               model=self.model, is_local=True)

    def complete(self, prompt: str, system: Optional[str] = None,
                 timeout: float = 60.0) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system
        if self.keep_alive is not None:
            payload["keep_alive"] = self.keep_alive
        data = _post_json(self.host + "/api/generate", payload, timeout)
        text = data.get("response")
        if not isinstance(text, str):
            raise PartnerError("ollama returned no 'response' field")
        return text.strip()


class OpenAICompatPartner(LLMPartner):
    """Any OpenAI-compatible /chat/completions endpoint.

    Covers hosted APIs, LM Studio, vLLM, llama.cpp's server, and Ollama's own
    compatibility route. The key is read from an environment variable named in
    config — never stored in config.json.
    """

    def __init__(self, model: str, base_url: str,
                 api_key_env: Optional[str] = None, is_local: bool = False):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env
        self._is_local = is_local

    @property
    def metadata(self) -> PartnerMetadata:
        return PartnerMetadata(name="{} @ {}".format(self.model, self.base_url),
                               provider="openai-compat", model=self.model,
                               is_local=self._is_local)

    def _headers(self) -> Dict[str, str]:
        if not self.api_key_env:
            return {}
        key = os.environ.get(self.api_key_env)
        if not key:
            raise PartnerError(
                "env var {} is not set (config references it for {})".format(
                    self.api_key_env, self.base_url))
        return {"Authorization": "Bearer " + key}

    def complete(self, prompt: str, system: Optional[str] = None,
                 timeout: float = 60.0) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": self.model, "messages": messages, "stream": False}
        data = _post_json(self.base_url + "/chat/completions", payload,
                          timeout, headers=self._headers())
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError, AttributeError) as e:
            raise PartnerError("unexpected chat/completions shape") from e


# --- config -> partner -------------------------------------------------------

DEFAULT_SLOTS = {
    "conscious": {"backend": "ollama", "model": "qwen3:8b"},
    "unconscious": {"backend": "ollama", "model": "qwen2.5-coder:7b"},
}


def partner_from_slot(slot: Dict[str, Any]) -> LLMPartner:
    """Build a partner from one slot's config dict."""
    backend = str(slot.get("backend", "ollama")).lower()
    model = slot.get("model")
    if not model:
        raise PartnerError("slot config has no 'model'")

    if backend == "ollama":
        return OllamaPartner(model=model,
                             host=slot.get("host", "http://127.0.0.1:11434"),
                             keep_alive=slot.get("keep_alive"))
    if backend in ("openai", "openai-compat", "api"):
        base_url = slot.get("base_url")
        if not base_url:
            raise PartnerError("openai-compat slot needs 'base_url'")
        return OpenAICompatPartner(model=model, base_url=base_url,
                                   api_key_env=slot.get("api_key_env"),
                                   is_local=bool(slot.get("is_local", False)))
    raise PartnerError("unknown backend: {}".format(backend))


def slots_from_config(config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Read slot config, falling back to the legacy scalar `model` key.

    Old installs have only config["model"]. Those keep working: the same model
    fills both slots, which is a valid (if uncalibratable) pair.
    """
    slots = config.get("slots")
    if isinstance(slots, dict) and "conscious" in slots and "unconscious" in slots:
        return slots
    legacy = config.get("model")
    if legacy:
        one = {"backend": "ollama", "model": legacy}
        return {"conscious": dict(one), "unconscious": dict(one)}
    return {k: dict(v) for k, v in DEFAULT_SLOTS.items()}


def partners_from_config(config: Dict[str, Any]) -> "tuple[LLMPartner, LLMPartner]":
    """Return (partner_for_conscious_slot, partner_for_unconscious_slot).

    These are *slot assignments from config*, not calibrated roles. The
    handshake decides which partner actually holds which role.
    """
    slots = slots_from_config(config)
    return (partner_from_slot(slots["conscious"]),
            partner_from_slot(slots["unconscious"]))

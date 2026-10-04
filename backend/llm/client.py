"""Pluggable LLM clients (Anthropic, OpenAI, Gemini, Groq)."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Optional

from backend.config import get_settings

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Raised for LLM configuration or call failures."""


class LLMClient(ABC):
    """Abstract LLM client."""

    @abstractmethod
    async def complete(
        self,
        system: str,
        user: str,
        schema: Optional[dict[str, Any]] = None,
        max_tokens: int = 2048,
    ) -> str | dict[str, Any]:
        """Return a completion.

        Args:
            system: System prompt.
            user: User prompt.
            schema: Optional JSON schema; when given, a dict is returned.
            max_tokens: Output token cap.

        Returns:
            Text, or a parsed dict when ``schema`` is supplied.
        """

    @abstractmethod
    def stream(
        self, system: str, user: str, max_tokens: int = 2048
    ) -> AsyncIterator[str]:
        """Stream text deltas."""

    @abstractmethod
    async def vision(
        self,
        system: str,
        user: str,
        image_bytes: bytes,
        media_type: str = "image/png",
        max_tokens: int = 1024,
    ) -> str:
        """Answer a question about an image."""


def _tool_def(schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": "emit",
        "description": "Return the structured result.",
        "input_schema": schema,
    }


def _schema_instruction(schema: dict[str, Any]) -> str:
    """Prompt suffix that makes a text-only model emit schema-shaped JSON."""
    return (
        "\n\nRespond with ONLY a single valid JSON object (no markdown fences, "
        "no commentary) that conforms to this JSON schema:\n"
        + json.dumps(schema)
    )


def _parse_json_object(raw: str) -> dict[str, Any]:
    """Parse a JSON object from model text, tolerating code fences.

    Args:
        raw: Raw model output.

    Returns:
        The parsed dict.

    Raises:
        LLMError: If no valid JSON object can be parsed.
    """
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise LLMError("Model did not return a JSON object")
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMError(f"Model returned invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LLMError("Model JSON output was not an object")
    return data


def _strip_unsupported_schema_keys(node: Any) -> Any:
    """Return a Gemini-compatible copy of a JSON schema.

    Gemini accepts an OpenAPI-style subset, so unsupported keywords are removed.
    """
    allowed = {"type", "properties", "items", "required", "enum", "description"}
    if isinstance(node, dict):
        return {
            k: _strip_unsupported_schema_keys(v)
            for k, v in node.items()
            if k in allowed or k in node.get("properties", {})
        }
    if isinstance(node, list):
        return [_strip_unsupported_schema_keys(v) for v in node]
    return node


class AnthropicClient(LLMClient):
    """Claude Sonnet client using tool-use for structured output."""

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise LLMError("ANTHROPIC_API_KEY is not set")
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def complete(
        self,
        system: str,
        user: str,
        schema: Optional[dict[str, Any]] = None,
        max_tokens: int = 2048,
    ) -> str | dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        if schema is not None:
            kwargs["tools"] = [_tool_def(schema)]
            kwargs["tool_choice"] = {"type": "tool", "name": "emit"}
        try:
            resp = await self._client.messages.create(**kwargs)
        except Exception as exc:  # noqa: BLE001 - SDK raises many types
            logger.error("Anthropic call failed: %s", type(exc).__name__)
            raise LLMError(f"Anthropic call failed: {exc}") from exc
        if schema is not None:
            for block in resp.content:
                if getattr(block, "type", "") == "tool_use":
                    return dict(block.input)
            raise LLMError("No structured output returned")
        return "".join(
            b.text for b in resp.content if getattr(b, "type", "") == "text"
        )

    async def stream(
        self, system: str, user: str, max_tokens: int = 2048
    ) -> AsyncIterator[str]:
        try:
            async with self._client.messages.stream(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            ) as s:
                async for delta in s.text_stream:
                    yield delta
        except Exception as exc:  # noqa: BLE001
            logger.error("Anthropic stream failed: %s", type(exc).__name__)
            raise LLMError(f"Anthropic stream failed: {exc}") from exc

    async def vision(
        self,
        system: str,
        user: str,
        image_bytes: bytes,
        media_type: str = "image/png",
        max_tokens: int = 1024,
    ) -> str:
        data = base64.b64encode(image_bytes).decode("ascii")
        content = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": data},
            },
            {"type": "text", "text": user},
        ]
        try:
            resp = await self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": content}],
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Anthropic vision failed: {exc}") from exc
        return "".join(
            b.text for b in resp.content if getattr(b, "type", "") == "text"
        )


class OpenAIClient(LLMClient):
    """OpenAI drop-in client."""

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise LLMError("OPENAI_API_KEY is not set")
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def complete(
        self,
        system: str,
        user: str,
        schema: Optional[dict[str, Any]] = None,
        max_tokens: int = 2048,
    ) -> str | dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if schema is not None:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": "emit",
                        "description": "Return the structured result.",
                        "parameters": schema,
                    },
                }
            ]
            kwargs["tool_choice"] = {"type": "function", "function": {"name": "emit"}}
        try:
            resp = await self._client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"OpenAI call failed: {exc}") from exc
        msg = resp.choices[0].message
        if schema is not None:
            if not msg.tool_calls:
                raise LLMError("No structured output returned")
            return json.loads(msg.tool_calls[0].function.arguments)
        return msg.content or ""

    async def stream(
        self, system: str, user: str, max_tokens: int = 2048
    ) -> AsyncIterator[str]:
        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                stream=True,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            async for chunk in resp:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"OpenAI stream failed: {exc}") from exc

    async def vision(
        self,
        system: str,
        user: str,
        image_bytes: bytes,
        media_type: str = "image/png",
        max_tokens: int = 1024,
    ) -> str:
        data = base64.b64encode(image_bytes).decode("ascii")
        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{media_type};base64,{data}"},
                            },
                        ],
                    },
                ],
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"OpenAI vision failed: {exc}") from exc
        return resp.choices[0].message.content or ""


class GeminiClient(LLMClient):
    """Google Gemini client (free tier) using ``google.generativeai``.

    Structured output is requested with a JSON response MIME type plus the
    schema; the result is parsed defensively.
    """

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        if not api_key:
            raise LLMError("GEMINI_API_KEY is not set")
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self._genai = genai
        self._model_name = model

    def _model(self, system: str, max_tokens: int, schema: Optional[dict[str, Any]]) -> Any:
        config: dict[str, Any] = {"max_output_tokens": max_tokens}
        if schema is not None:
            config["response_mime_type"] = "application/json"
        return self._genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=system,
            generation_config=config,
        )

    async def complete(
        self,
        system: str,
        user: str,
        schema: Optional[dict[str, Any]] = None,
        max_tokens: int = 2048,
    ) -> str | dict[str, Any]:
        prompt = user
        if schema is not None:
            prompt = user + _schema_instruction(_strip_unsupported_schema_keys(schema))
        model = self._model(system, max_tokens, schema)
        try:
            resp = await model.generate_content_async(prompt)
            text = resp.text or ""
        except Exception as exc:  # noqa: BLE001 - SDK raises many types
            logger.error("Gemini call failed: %s", type(exc).__name__)
            raise LLMError(f"Gemini call failed: {exc}") from exc
        if schema is not None:
            return _parse_json_object(text)
        return text

    async def stream(
        self, system: str, user: str, max_tokens: int = 2048
    ) -> AsyncIterator[str]:
        model = self._model(system, max_tokens, None)
        try:
            resp = await model.generate_content_async(user, stream=True)
            async for chunk in resp:
                try:
                    piece = chunk.text
                except ValueError:
                    piece = ""
                if piece:
                    yield piece
        except Exception as exc:  # noqa: BLE001
            logger.error("Gemini stream failed: %s", type(exc).__name__)
            raise LLMError(f"Gemini stream failed: {exc}") from exc

    async def vision(
        self,
        system: str,
        user: str,
        image_bytes: bytes,
        media_type: str = "image/png",
        max_tokens: int = 1024,
    ) -> str:
        model = self._model(system, max_tokens, None)
        parts = [{"mime_type": media_type, "data": image_bytes}, user]
        try:
            resp = await model.generate_content_async(parts)
            return resp.text or ""
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Gemini vision failed: {exc}") from exc


class GroqClient(LLMClient):
    """Groq client (free tier, fast) for text-only completions."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile") -> None:
        if not api_key:
            raise LLMError("GROQ_API_KEY is not set")
        from groq import AsyncGroq

        self._client = AsyncGroq(api_key=api_key)
        self._model = model

    async def complete(
        self,
        system: str,
        user: str,
        schema: Optional[dict[str, Any]] = None,
        max_tokens: int = 2048,
    ) -> str | dict[str, Any]:
        prompt = user
        kwargs: dict[str, Any] = {}
        if schema is not None:
            prompt = user + _schema_instruction(schema)
            kwargs["response_format"] = {"type": "json_object"}
        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                **kwargs,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Groq call failed: %s", type(exc).__name__)
            raise LLMError(f"Groq call failed: {exc}") from exc
        text = resp.choices[0].message.content or ""
        if schema is not None:
            return _parse_json_object(text)
        return text

    async def stream(
        self, system: str, user: str, max_tokens: int = 2048
    ) -> AsyncIterator[str]:
        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                stream=True,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            async for chunk in resp:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as exc:  # noqa: BLE001
            logger.error("Groq stream failed: %s", type(exc).__name__)
            raise LLMError(f"Groq stream failed: {exc}") from exc

    async def vision(
        self,
        system: str,
        user: str,
        image_bytes: bytes,
        media_type: str = "image/png",
        max_tokens: int = 1024,
    ) -> str:
        raise NotImplementedError(
            "GroqClient does not support image input with llama-3.3-70b-versatile. "
            "Set LLM_PROVIDER to 'gemini', 'anthropic' or 'openai' for Show Me / "
            "screenshot analysis."
        )


def get_llm_client() -> LLMClient:
    """Build the client selected by ``LLM_PROVIDER``.

    Supported values: ``anthropic``, ``openai``, ``gemini``, ``groq``.

    Returns:
        A configured :class:`LLMClient`.

    Raises:
        LLMError: If the provider is unknown or its key is missing.
    """
    s = get_settings()
    provider = s.llm_provider.lower()
    if provider == "anthropic":
        return AnthropicClient(s.anthropic_api_key or "", s.anthropic_model)
    if provider == "openai":
        return OpenAIClient(s.openai_api_key or "", s.openai_model)
    if provider == "gemini":
        return GeminiClient(s.gemini_api_key or "", s.gemini_model)
    if provider == "groq":
        return GroqClient(s.groq_api_key or "", s.groq_model)
    raise LLMError(f"Unknown LLM_PROVIDER: {s.llm_provider}")


# Keep asyncio imported for downstream helpers that may schedule blocking SDK calls.
_ = asyncio
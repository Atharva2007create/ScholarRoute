from __future__ import annotations

from importlib import import_module
from typing import Any, Protocol

from pydantic import BaseModel


class AIProviderError(Exception):
    def __init__(self, category: str, *, transient: bool = False) -> None:
        super().__init__(category)
        self.category = category
        self.transient = transient


class AIProvider(Protocol):
    def generate(
        self,
        *,
        model: str,
        system_instruction: str,
        prompt: str,
        response_schema: type[BaseModel],
        timeout_seconds: int,
        max_output_tokens: int,
    ) -> Any: ...


class GeminiProvider:
    """Direct official Google Gen AI SDK adapter with SDK retries disabled."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def generate(
        self,
        *,
        model: str,
        system_instruction: str,
        prompt: str,
        response_schema: type[BaseModel],
        timeout_seconds: int,
        max_output_tokens: int,
    ) -> Any:
        genai = import_module("google.genai")
        errors = import_module("google.genai.errors")
        types = import_module("google.genai.types")
        client = genai.Client(
            api_key=self._api_key,
            http_options=types.HttpOptions(
                timeout=timeout_seconds * 1000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        schema = {
            "type": "OBJECT",
            "properties": {
                "summary": {"type": "STRING", "min_length": 1, "max_length": 700},
                "reasons": {
                    "type": "ARRAY",
                    "items": {"type": "STRING", "min_length": 1, "max_length": 300},
                    "min_items": 1,
                    "max_items": 5,
                },
                "caveats": {
                    "type": "ARRAY",
                    "items": {"type": "STRING", "min_length": 1, "max_length": 300},
                    "max_items": 4,
                },
                "next_steps": {
                    "type": "ARRAY",
                    "items": {"type": "STRING", "min_length": 1, "max_length": 300},
                    "min_items": 1,
                    "max_items": 4,
                },
            },
            "required": ["summary", "reasons", "caveats", "next_steps"],
        }
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.1,
                    candidate_count=1,
                    max_output_tokens=max_output_tokens,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )
        except errors.APIError as exc:
            code = int(exc.code)
            if code == 429:
                raise AIProviderError("rate_limited", transient=True) from exc
            if code in {408, 500, 502, 503, 504}:
                raise AIProviderError("provider_unavailable", transient=True) from exc
            if code in {400, 401, 403}:
                raise AIProviderError("invalid_credentials") from exc
            raise AIProviderError("provider_error") from exc
        except TimeoutError as exc:
            raise AIProviderError("timeout", transient=True) from exc
        except Exception as exc:
            if "timeout" in type(exc).__name__.lower():
                raise AIProviderError("timeout", transient=True) from exc
            raise AIProviderError("provider_unavailable", transient=True) from exc
        finally:
            client.close()
        if response.parsed is not None:
            return response.parsed
        if not response.text:
            raise AIProviderError("empty_response")
        return response.text

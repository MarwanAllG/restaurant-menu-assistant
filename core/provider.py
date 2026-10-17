"""OpenRouter Chat Completions through LangChain."""

from __future__ import annotations

from contextlib import contextmanager

import openai
from langchain_core.messages import AIMessage, message_chunk_to_message
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from core.config import Settings


class ConfigurationError(RuntimeError):
    pass


PROVIDER_MESSAGES = {
    "model_access": "The configured AI model isn’t available to this app. Please ask the demo owner to check model access.",
    "authentication": "The language service could not authenticate this app. Please ask the demo owner to check its configuration.",
    "credits": "The language service has no available credits. Please ask the demo owner to check the provider account.",
    "rate_limit": "The language service is busy. Please try again in a moment.",
    "unavailable": "The language service is temporarily unavailable. Please try again shortly.",
    "request": "The language service rejected this app’s request. Please ask the demo owner to check the integration.",
}
PROVIDER_ACTIONS = {
    "model_access": "Provider denied model access; check MODEL_NAME and account permissions",
    "authentication": "Provider rejected authentication; check the configured provider’s API key",
    "credits": "Provider has no available credits; check account billing",
    "rate_limit": "Provider rate limit reached; try again later",
    "unavailable": "Provider could not be reached or is unavailable; check connectivity and service status",
    "request": "Provider rejected the integration request; check the endpoint, model and request schema",
}


class ProviderError(RuntimeError):
    """A controlled operator diagnostic: never retain raw bodies, prompts or credentials."""

    def __init__(self, reason: str, status_code: int | None = None):
        self.reason = reason
        self.status_code = status_code
        suffix = f" (HTTP {status_code})" if status_code is not None else ""
        super().__init__(PROVIDER_ACTIONS[reason] + suffix)


@contextmanager
def provider_errors():
    try:
        yield
    except openai.APIStatusError as exc:
        reason = {
            401: "authentication",
            402: "credits",
            403: "model_access",
            429: "rate_limit",
        }.get(exc.status_code, "unavailable" if exc.status_code >= 500 else "request")
        raise ProviderError(reason, exc.status_code) from None
    except openai.APIConnectionError:
        # APITimeoutError (including LangChain's subclass) also inherits this type.
        raise ProviderError("unavailable") from None


class ChatModel:
    def __init__(self, settings: Settings):
        if not settings.api_key:
            raise ConfigurationError("Add OPENROUTER_API_KEY to .env")
        self.llm = ChatOpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            model=settings.model,
            temperature=0,
            timeout=settings.timeout,
            max_retries=0,
            use_responses_api=False,
            extra_body={
                "max_tokens": settings.max_output_tokens,
                "provider": {"require_parameters": True},
                "reasoning": (
                    {"enabled": False}
                    if settings.reasoning_effort == "none"
                    else {"effort": settings.reasoning_effort}
                ),
            },
        )

    def structured(self, schema: type[BaseModel], messages):
        # LangChain converts Pydantic to the provider's strict JSON schema, then validates it.
        with provider_errors():
            return self.llm.with_structured_output(
                schema, method="json_schema", strict=True
            ).invoke(messages)

    def tool_turn(self, messages, tools) -> AIMessage:
        bound = self.llm.bind_tools(tools, tool_choice="required", strict=True)
        combined = None
        finish_reason = None
        with provider_errors():
            for chunk in bound.stream(messages):
                # OpenRouter can repeat terminal status in its usage chunk. LangChain's
                # generic chunk merge concatenates strings, including finish_reason.
                if chunk.response_metadata.get("finish_reason") is not None:
                    finish_reason = chunk.response_metadata["finish_reason"]
                combined = chunk if combined is None else combined + chunk
        if combined is None:
            raise ValueError("Empty provider response")
        result = message_chunk_to_message(combined)
        result.response_metadata["finish_reason"] = finish_reason
        if finish_reason not in {None, "stop", "tool_calls"}:
            raise ValueError("Incomplete or refused tool response")
        if result.invalid_tool_calls:
            raise ValueError("Malformed tool-call arguments")
        return result

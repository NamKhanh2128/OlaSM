import hashlib
import json
import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from openai import AsyncOpenAI, OpenAIError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelToolCall:
    name: str
    arguments: dict[str, Any]
    call_id: str = "model-tool-call"


@dataclass(frozen=True)
class ToolExchange:
    call: ModelToolCall
    result: dict[str, Any]


@dataclass(frozen=True)
class ModelDecision:
    message: str | None = None
    tool_call: ModelToolCall | None = None


class ConversationModel(Protocol):
    async def decide(
        self,
        *,
        instructions: str,
        context: dict[str, Any],
        tools: Sequence[dict[str, Any]],
        exchanges: Sequence[ToolExchange] = (),
    ) -> ModelDecision: ...


class ConversationModelError(RuntimeError):
    pass


class OpenAIConversationModel:
    """Thin provider adapter; orchestration remains provider independent."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
        reasoning_effort: str = "none",
        base_url: str | None = None,
        client: AsyncOpenAI | None = None,
    ) -> None:
        if not api_key and client is None:
            raise ValueError("OpenAI API key is required")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.reasoning_effort = reasoning_effort
        self.client = client or AsyncOpenAI(api_key=api_key, base_url=base_url, max_retries=0)

    async def decide(
        self,
        *,
        instructions: str,
        context: dict[str, Any],
        tools: Sequence[dict[str, Any]],
        exchanges: Sequence[ToolExchange] = (),
    ) -> ModelDecision:
        kwargs: dict[str, Any] = {"reasoning_effort": self.reasoning_effort}
        start = time.perf_counter()
        usage: dict[str, Any] | None = None
        preview = json.dumps(context, ensure_ascii=False, separators=(",", ":"))[:500]
        try:
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": instructions},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False, separators=(",", ":"))},
            ]
            for exchange in exchanges:
                messages.extend(
                    [
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": exchange.call.call_id,
                                    "type": "function",
                                    "function": {
                                        "name": exchange.call.name,
                                        "arguments": json.dumps(exchange.call.arguments, ensure_ascii=False),
                                    },
                                }
                            ],
                        },
                        {
                            "role": "tool",
                            "tool_call_id": exchange.call.call_id,
                            "content": json.dumps(exchange.result, ensure_ascii=False),
                        },
                    ]
                )
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=list(tools),
                tool_choice="auto",
                parallel_tool_calls=False,
                max_completion_tokens=600,
                timeout=self.timeout_seconds,
                **kwargs,
            )
            usage = getattr(response, "usage", None)
            if usage is not None and not isinstance(usage, dict):
                try:
                    usage = usage.model_dump()  # type: ignore[union-attr]
                except Exception:
                    usage = {"raw": str(usage)[:500]}
        except (OpenAIError, TimeoutError, ValueError) as exc:
            logger.warning(
                "Conversation model request failed: model=%s error_type=%s",
                self.model,
                type(exc).__name__,
            )
            raise ConversationModelError("conversation model failed") from exc

        latency_ms = (time.perf_counter() - start) * 1000
        try:
            from src.backend.observability.langfuse_client import get_langfuse

            client = get_langfuse()
            if client is not None:
                trace = client.trace(
                    name="agent_llm_decide",
                    metadata={"model": self.model, "latency_ms": round(latency_ms, 2)},
                    input=hashlib.sha256(preview.encode()).hexdigest()[:16],
                )
                gen = trace.generation(
                    name="agent_llm_decide",
                    model=self.model,
                    input=hashlib.sha256(preview.encode()).hexdigest()[:16],
                    metadata={"latency_ms": round(latency_ms, 2)},
                    usage=usage if isinstance(usage, dict) else None,
                )
                try:
                    gen.end()
                except Exception:
                    pass
        except Exception:
            pass

        message = response.choices[0].message  # type: ignore[possibly-undefined]
        if message.tool_calls:
            call = message.tool_calls[0]
            try:
                arguments = json.loads(call.function.arguments)
            except (json.JSONDecodeError, TypeError) as exc:
                raise ConversationModelError("model returned invalid tool arguments") from exc
            if not isinstance(arguments, dict):
                raise ConversationModelError("model tool arguments must be an object")
            return ModelDecision(tool_call=ModelToolCall(call.function.name, arguments, call.id))
        content = (message.content or "").strip()
        if not content:
            raise ConversationModelError("model returned no message or tool call")
        return ModelDecision(message=content)


def build_conversation_model() -> ConversationModel:
    from src.config import get_settings

    settings = get_settings()
    if not settings.agent_llm_enabled:
        raise ValueError("model-driven agent requires AGENT_LLM_ENABLED=true")
    return OpenAIConversationModel(
        api_key=settings.llm_api_key_for(settings.agent_llm_base_url),
        model=settings.agent_llm_model,
        timeout_seconds=settings.agent_llm_timeout_seconds,
        reasoning_effort=settings.agent_llm_reasoning_effort,
        base_url=settings.agent_llm_base_url,
    )

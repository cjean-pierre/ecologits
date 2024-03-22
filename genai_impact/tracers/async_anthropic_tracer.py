from typing import Any, Callable

from wrapt import wrap_function_wrapper

from genai_impact.compute_impacts import Impacts, compute_llm_impact
from genai_impact.model_repository import models

try:
    from anthropic import AsyncAnthropic as _Anthropic
    from anthropic.types import Message as _Message
except ImportError:
    _Anthropic = object()
    _Message = object()


class Message(_Message):
    impacts: Impacts


async def anthropic_chat_wrapper(
    wrapped: Callable, instance: _Anthropic, args: Any, kwargs: Any  # noqa: ARG001
) -> Message:
    print("anthropic_chat_wrapper")
    response = await wrapped(*args, **kwargs)
    model = models.find_model(provider="anthropic", model_name=response.model)
    if model is None:
        # TODO: Replace with proper logging
        print(f"Could not find model `{response.model}` for anthropic provider.")
        return response
    output_tokens = response.usage.output_tokens
    model_size = model.active_parameters or model.active_parameters_range
    impacts = compute_llm_impact(
        model_parameter_count=model_size, output_token_count=output_tokens
    )
    return Message(**response.model_dump(), impacts=impacts)


class AsyncAnthropicInstrumentor:
    def __init__(self) -> None:
        self.wrapped_methods = [
            {
                "module": "anthropic.resources",
                "name": "AsyncMessages.create",
                "wrapper": anthropic_chat_wrapper,
            },
        ]

    def instrument(self) -> None:
        for wrapper in self.wrapped_methods:
            wrap_function_wrapper(
                wrapper["module"], wrapper["name"], wrapper["wrapper"]
            )

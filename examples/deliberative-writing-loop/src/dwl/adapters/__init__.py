from .anthropic import AnthropicAdapter
from .base import Budget, BudgetExceeded, LLMAdapter, LLMResponse, MockAdapter
from .openai import OpenAIAdapter
from .pangram import PangramClient

__all__ = [
    "AnthropicAdapter",
    "Budget",
    "BudgetExceeded",
    "LLMAdapter",
    "LLMResponse",
    "MockAdapter",
    "OpenAIAdapter",
    "PangramClient",
]


def make_adapter(provider: str, model: str | None = None, budget: Budget | None = None) -> LLMAdapter:
    provider = provider.lower()
    if provider == "anthropic":
        return AnthropicAdapter(model=model, budget=budget)
    if provider == "openai":
        return OpenAIAdapter(model=model, budget=budget)
    if provider == "mock":
        return MockAdapter(budget=budget)
    raise ValueError(f"unknown provider: {provider!r} (expected anthropic, openai, or mock)")

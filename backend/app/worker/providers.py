import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any, Protocol

from openai import AsyncOpenAI

from app.config import settings


@dataclass
class Completion:
    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_usd: float


class Provider(Protocol):
    async def complete(self, prompt: str, config: dict[str, Any]) -> Completion: ...


class MockProvider:
    """Echoes the prompt. Free and offline: use it to test the pipeline."""

    async def complete(self, prompt: str, config: dict[str, Any]) -> Completion:
        start = time.perf_counter()
        await asyncio.sleep(random.uniform(0.05, 0.2))
        words = len(prompt.split())
        return Completion(prompt, words, words, int((time.perf_counter() - start) * 1000), 0.0)


# USD per 1M tokens: (input, output). Verify against https://openai.com/api/pricing
PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
}


class OpenAIProvider:
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.client = AsyncOpenAI(api_key=settings.openai_api_key, max_retries=3, timeout=60)

    async def complete(self, prompt: str, config: dict[str, Any]) -> Completion:
        start = time.perf_counter()
        resp = await self.client.chat.completions.create(
            model=config["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=config["temperature"],
            # Newer OpenAI models reject max_tokens; max_completion_tokens works across them.
            max_completion_tokens=config["max_tokens"],
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        usage = resp.usage
        in_tok = usage.prompt_tokens if usage else 0
        out_tok = usage.completion_tokens if usage else 0
        in_price, out_price = PRICING.get(config["model"], (0.0, 0.0))
        return Completion(
            text=resp.choices[0].message.content or "",
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_ms=latency_ms,
            cost_usd=(in_tok * in_price + out_tok * out_price) / 1_000_000,
        )


_FACTORIES: dict[str, type] = {"mock": MockProvider, "openai": OpenAIProvider}
_providers: dict[str, Provider] = {}


def get_provider(name: str) -> Provider:
    if name not in _providers:
        if name not in _FACTORIES:
            raise ValueError(f"unknown provider '{name}'")
        _providers[name] = _FACTORIES[name]()
    return _providers[name]

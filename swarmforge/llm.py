"""LLM backends. Every call returns a schema-validated pydantic object or raises LLMError."""
from __future__ import annotations

import json
import os
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = os.getenv("SWARMFORGE_MODEL", "claude-opus-5-5")


class LLMError(RuntimeError):
    pass


class LLM(Protocol):
    def structured(self, system: str, prompt: str, schema: type[T]) -> T: ...


def _strict_schema(schema: type[BaseModel]) -> dict:
    """Structured outputs require additionalProperties: false on every object."""
    s = schema.model_json_schema()

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node.setdefault("required", list(node.get("properties", {})))
            for k in ("minimum", "maximum", "maxLength"):  # keep the API schema simple;
                node.pop(k, None)                           # pydantic re-validates below
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(s)
    return s


class ClaudeLLM:
    """Claude via the Anthropic SDK: JSON-schema output, adaptive thinking, server-side refusal fallback."""

    def __init__(self, model: str = DEFAULT_MODEL, effort: str = "high", client=None):
        import anthropic

        self._anthropic = anthropic
        self.client = client or anthropic.Anthropic(max_retries=3, timeout=300.0)
        self.model = model
        self.effort = effort

    def structured(self, system: str, prompt: str, schema: type[T]) -> T:
        a = self._anthropic
        try:
            resp = self.client.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                thinking={"type": "adaptive"},
                output_config={
                    "effort": self.effort,
                    "format": {"type": "json_schema", "schema": _strict_schema(schema)},
                },
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except a.RateLimitError as e:
            raise LLMError(f"rate limited: {e}") from e
        except a.APIStatusError as e:
            raise LLMError(f"API error {e.status_code}: {e.message}") from e
        except a.APIConnectionError as e:
            raise LLMError(f"connection error: {e}") from e

        if resp.stop_reason == "refusal":
            cat = getattr(resp.stop_details, "category", None) if resp.stop_details else None
            raise LLMError(f"model declined (category={cat})")
        if resp.stop_reason == "max_tokens":
            raise LLMError("output truncated at max_tokens")
        text = next((b.text for b in resp.content if b.type == "text"), None)
        if text is None:
            raise LLMError("no text block in response")
        try:
            return schema.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValidationError) as e:
            raise LLMError(f"schema validation failed: {e}") from e


class FakeLLM:
    """Deterministic offline backend for tests and demo mode (no API key needed)."""

    def __init__(self, irreversible: bool = False, fail_experts: set[str] | None = None):
        self.irreversible = irreversible
        self.fail_experts = fail_experts or set()
        self.calls: list[tuple[str, str]] = []

    def structured(self, system: str, prompt: str, schema: type[T]) -> T:
        from .schemas import Critique, Proposal, Verdict

        self.calls.append((schema.__name__, system[:60]))
        for name in self.fail_experts:
            if name in system:
                raise LLMError(f"simulated failure for {name}")
        if schema is Proposal:
            return Proposal(
                title=f"Plan from: {system.split('.')[0][:60]}",
                rationale="Offline demo proposal.",
                first_principles=["Value is delivered only when a real user benefits"],
                steps=["Define one measurable outcome", "Ship smallest test", "Measure"],
                risks=["Demo data is not real"],
                reversible=not self.irreversible,
                confidence=0.5,
            )
        if schema is Critique:
            score = 3 + len(self.calls) % 5
            return Critique(fatal_flaws=[], weaknesses=["Untested"], hidden_assumptions=["Demand exists"], score=score)
        if schema is Verdict:
            return Verdict(
                chosen_index=0, why="Highest critic score.", next_step="Write the outcome as one sentence.",
                success_metric="One user confirms value", dissent="Sample size of one.",
            )
        raise LLMError(f"FakeLLM has no stub for {schema.__name__}")

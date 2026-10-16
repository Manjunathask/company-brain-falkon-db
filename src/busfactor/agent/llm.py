"""Small provider seam for the agent loop. A future OpenAI adapter can implement LLM."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


@dataclass
class Step:
    stop: Literal["tool_use", "end", "refusal", "max_tokens"]
    text: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    raw_assistant_content: Any = None
    usage: dict = field(default_factory=dict)


class LLM(Protocol):
    def step(self, system: str, messages: list, tools: list[dict]) -> Step: ...
    def assistant_message(self, step: Step) -> dict: ...
    def tool_results_message(self, results: list[dict]) -> dict: ...


class AnthropicLLM:
    def __init__(self, client=None, model: str | None = None, effort: str | None = None):
        import anthropic
        kwargs = {}
        workspace = os.getenv("ANTHROPIC_WORKSPACE_ID")
        if workspace:
            kwargs["default_headers"] = {"anthropic-workspace-id": workspace}
        self.client = client or anthropic.Anthropic(**kwargs)
        self.model = model or os.getenv("AGENT_MODEL", "claude-sonnet-5-5")
        self.effort = effort or os.getenv("AGENT_EFFORT", "medium")

    def step(self, system: str, messages: list, tools: list[dict]) -> Step:
        response = self.client.beta.messages.create(
            model=self.model,
            max_tokens=16000,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=messages,
            tools=tools,
            tool_choice={"type": "auto"},
            output_config={"effort": self.effort},
            stream=False,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        stop = response.stop_reason
        usage = _model_dict(getattr(response, "usage", None))
        if stop == "refusal":
            return Step("refusal", "", [], response.content, usage)
        blocks = response.content
        text = "".join(getattr(block, "text", "") for block in blocks if getattr(block, "type", None) == "text")
        calls = [{"id": block.id, "name": block.name, "input": block.input}
                 for block in blocks if getattr(block, "type", None) == "tool_use"]
        kind = "tool_use" if stop == "tool_use" else "max_tokens" if stop == "max_tokens" else "end"
        return Step(kind, text, calls, blocks, usage)

    def assistant_message(self, step: Step) -> dict:
        return {"role": "assistant", "content": step.raw_assistant_content or []}

    def tool_results_message(self, results: list[dict]) -> dict:
        content = []
        for result in results:
            block = {"type": "tool_result", "tool_use_id": result["id"], "content": result["content"]}
            if result.get("is_error"):
                block["is_error"] = True
            content.append(block)
        return {"role": "user", "content": content}


class ScriptedLLM:
    """Replay deterministic steps without network access."""
    def __init__(self, steps: list[Step | dict]):
        self.steps = [step if isinstance(step, Step) else Step(**step) for step in steps]
        self.seen_messages: list[list] = []

    def step(self, system: str, messages: list, tools: list[dict]) -> Step:
        self.seen_messages.append(list(messages))
        if not self.steps:
            raise RuntimeError("ScriptedLLM has no remaining steps")
        return self.steps.pop(0)

    def assistant_message(self, step: Step) -> dict:
        if step.raw_assistant_content is not None:
            return {"role": "assistant", "content": step.raw_assistant_content}
        content = ([{"type": "text", "text": step.text}] if step.text else [])
        content += [{"type": "tool_use", "id": call.get("id", f"script-{n}"),
                     "name": call["name"], "input": call.get("input", {})}
                    for n, call in enumerate(step.tool_calls)]
        return {"role": "assistant", "content": content}

    def tool_results_message(self, results: list[dict]) -> dict:
        return {"role": "user", "content": [{
            "type": "tool_result", "tool_use_id": result["id"], "content": result["content"],
            **({"is_error": True} if result.get("is_error") else {}),
        } for result in results]}


def create_llm():
    provider = os.getenv("AGENT_PROVIDER", "anthropic").lower()
    if provider == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("Set ANTHROPIC_API_KEY to enable agent chat")
        return AnthropicLLM()
    if provider == "scripted":
        raw = os.getenv("AGENT_SCRIPT")
        if not raw:
            raise ValueError("AGENT_SCRIPT must contain a JSON list of scripted steps")
        return ScriptedLLM(json.loads(raw))
    raise ValueError("AGENT_PROVIDER must be 'anthropic' or 'scripted'")


def _model_dict(value):
    if value is None: return {}
    if hasattr(value, "model_dump"): return value.model_dump()
    return dict(value) if isinstance(value, dict) else {}

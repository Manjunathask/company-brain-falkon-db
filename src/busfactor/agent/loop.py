"""Bounded tool loop; all graph facts in an answer must have a returned graph-tool result."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import time
import uuid

from busfactor import tools as graph_tools
from busfactor.db import get_graph
from .llm import Step
from .memory import Memory, entity_keys
from .prompt import SYSTEM_PROMPT

MAX_TOOL_RESULT_ROWS = 40
MAX_LIST_ITEMS = 10
MAX_STRING_CHARS = 2000

TOOL_ORDER = ["bus_factor", "bus_factor_component", "departure_impact", "departure_files",
              "orphaned_decisions", "decision_share", "successor", "simulate_departure", "bridges",
              "groups", "decision_trace", "why_not", "drift", "declared_vs_actual", "find_entity",
              "remember_correction"]
PARAMS = {
    "bus_factor": {"since":"integer", "minCommits":"integer", "minTotal":"integer"},
    "bus_factor_component": {"since":"integer", "minCommits":"integer", "minTotal":"integer"},
    "departure_impact": {"login":"string", "since":"integer", "minCommits":"integer"},
    "departure_files": {"login":"string", "since":"integer"},
    "orphaned_decisions": {"login":"string", "minConfidence":"string"},
    "decision_share": {"login":"string", "minShare":"number", "minConfidence":"string"},
    "successor": {"login":"string", "component":"string", "since":"integer"},
    "simulate_departure": {"login":"string"}, "bridges": {"limit":"integer"}, "groups": {},
    "decision_trace": {"path":"string", "limit":"integer"}, "why_not": {"slug":"string"},
    "drift": {"minConfidence":"string"},
    "declared_vs_actual": {"since":"integer", "minCommits":"integer"},
    "find_entity": {"text":"string", "limit":"integer"},
    "remember_correction": {"key":"string", "text":"string", "source":"string"},
}
REQUIRED = {"departure_impact":["login"], "departure_files":["login"], "orphaned_decisions":["login"],
            "decision_share":["login"], "successor":["login","component"], "simulate_departure":["login"],
            "decision_trace":["path"], "why_not":["slug"], "remember_correction":["key","text"]}


def tool_specs() -> list[dict]:
    specs = []
    for name in TOOL_ORDER:
        function = graph_tools.TOOLS.get(name)
        description = function.__doc__ if function else "Store a user's correction in their memory graph; this does not modify delta."
        props = {key: {"type": kind} for key, kind in PARAMS[name].items()}
        specs.append({"name": name, "description": description,
                      "input_schema": {"type":"object", "properties":props,
                                       "required":REQUIRED.get(name, []), "additionalProperties":False},
                      "strict": True})
    return specs


def _validate(name: str, params: object) -> tuple[dict | None, str | None]:
    if name not in PARAMS: return None, f"Unknown tool: {name}"
    if not isinstance(params, dict): return None, "Tool input must be an object"
    unknown = set(params) - set(PARAMS[name])
    missing = set(REQUIRED.get(name, [])) - set(params)
    if unknown: return None, f"Unexpected input fields: {', '.join(sorted(unknown))}"
    if missing: return None, f"Missing required fields: {', '.join(sorted(missing))}"
    for key, value in params.items():
        kind = PARAMS[name][key]
        valid = (isinstance(value, str) if kind == "string" else
                 isinstance(value, (int, float)) and not isinstance(value, bool) if kind == "number" else
                 isinstance(value, int) and not isinstance(value, bool))
        if not valid: return None, f"{key} must be {kind}"
    if name == "remember_correction" and not any(params["key"].startswith(prefix + ":") for prefix in ("person", "component", "module", "decision")):
        return None, "key must use person:, component:, module:, or decision:"
    return params, None


def _merge_graph(target: dict, source: dict) -> None:
    nodes = {node.get("id"): node for node in target["nodes"]}
    for node in source.get("nodes", []): nodes.setdefault(node.get("id"), node)
    target["nodes"] = list(nodes.values())
    edges = {(edge.get("source"), edge.get("type"), edge.get("target")): edge for edge in target["edges"]}
    for edge in source.get("edges", []): edges.setdefault((edge.get("source"), edge.get("type"), edge.get("target")), edge)
    target["edges"] = list(edges.values())


def _compact_rows(rows: list[dict]) -> list[dict]:
    """Bound tool-result context by trimming long strings and replacing long lists with a preview and omitted count."""
    def compact(value):
        if isinstance(value, str) and len(value) > MAX_STRING_CHARS:
            return value[:MAX_STRING_CHARS] + f"… ({len(value) - MAX_STRING_CHARS} characters omitted)"
        if isinstance(value, list):
            preview = [compact(item) for item in value[:MAX_LIST_ITEMS]]
            if len(value) > MAX_LIST_ITEMS:
                return {"items": preview, "truncated": len(value) - MAX_LIST_ITEMS}
            return preview
        if isinstance(value, dict):
            return {key: compact(item) for key, item in value.items()}
        return value
    return [compact(row) for row in rows[:MAX_TOOL_RESULT_ROWS]]


def _tool_result_chars(result: dict) -> int:
    block = {"type": "tool_result", "tool_use_id": result["id"], "content": result["content"]}
    if result.get("is_error"):
        block["is_error"] = True
    return len(json.dumps(block, ensure_ascii=False))


def _first_user_message(question: str, today: str, recalled: list[dict]) -> str:
    sections = [f"Today is {today}."]
    if recalled:
        labels = {"entity":"Entity", "lastAsked":"Last asked", "earlierQuestions":"Earlier questions",
                  "corrections":"Corrections", "changedSinceLastAsked":"Changes since then"}
        entries = []
        for item in recalled:
            lines = []
            for key, value in item.items():
                if value is None or value == [] or value == {}:
                    continue
                rendered = json.dumps(value, ensure_ascii=False, default=str)
                lines.append(f"  {labels.get(key, key)}: {rendered}")
            if lines:
                entries.append("\n".join(lines))
        if entries:
            sections.append("What you remember about this user:\n" + "\n".join(entries))
    sections.append(f"Question: {question}")
    return "\n\n".join(sections)


def ask(question: str, user: str, session_id: str | None = None, llm=None, *, memory: Memory | None = None,
        graph=None, max_rounds: int = 8) -> dict:
    if llm is None:
        from .llm import create_llm
        llm = create_llm()
    graph = graph or get_graph()
    memory = memory or Memory(user)
    session_id = session_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    recalled = memory.recall(delta_graph=graph)
    messages = [{"role":"user", "content":_first_user_message(question, now.date().isoformat(), recalled)}]
    evidence = {"nodes": [], "edges": []}
    trail, entities, usages = [], set(), []
    successful_tool_count = 0
    stop_reason = "end"
    rounds = 0
    while True:
        available = tool_specs() if rounds < max_rounds else []
        step = llm.step(SYSTEM_PROMPT, messages, available)
        usages.append(step.usage or {})
        messages.append(llm.assistant_message(step))
        if step.stop == "tool_use" and rounds < max_rounds:
            rounds += 1
            results = []
            for call in step.tool_calls:
                name, call_id, raw = call.get("name", ""), call.get("id", str(uuid.uuid4())), call.get("input", {})
                params, error = _validate(name, raw)
                start = time.perf_counter()
                try:
                    if error: raise ValueError(error)
                    if name == "remember_correction":
                        result = memory.store_correction(**params)
                    else:
                        result = graph_tools.TOOLS[name](**params)
                    successful_tool_count += 1
                    elapsed = round((time.perf_counter() - start) * 1000, 2)
                    rows = result.get("rows", [])
                    trail.append({"tool":name, "params":params, "cypher":result.get("cypher", ""),
                                  "row_count":len(rows), "ms":elapsed})
                    _merge_graph(evidence, result.get("graph", {}))
                    entities.update(entity_keys(result.get("graph", {})))
                    payload = {"tool":name, "row_count":len(rows), "rows":_compact_rows(rows)}
                    if len(rows) > MAX_TOOL_RESULT_ROWS:
                        payload["truncated"] = len(rows) - MAX_TOOL_RESULT_ROWS
                    tool_result = {"id":call_id, "content":json.dumps(payload, ensure_ascii=False, default=str)}
                    results.append(tool_result)
                    trail[-1]["tool_result_chars"] = _tool_result_chars(tool_result)
                except Exception as exc:
                    elapsed = round((time.perf_counter() - start) * 1000, 2)
                    tool_result = {"id":call_id, "content":str(exc), "is_error":True}
                    results.append(tool_result)
                    trail.append({"tool":name or "unknown", "params":raw, "cypher":"", "row_count":0, "ms":elapsed})
                    trail[-1]["tool_result_chars"] = _tool_result_chars(tool_result)
            messages.append(llm.tool_results_message(results))
            if rounds >= max_rounds:
                stop_reason = "round_limit"
                messages.append({"role":"user", "content":"Tool round limit reached. Give the best evidence-based summary now."})
                final = llm.step(SYSTEM_PROMPT, messages, [])
                usages.append(final.usage or {})
                messages.append(llm.assistant_message(final))
                answer = final.text
                if final.stop != "end": stop_reason = final.stop
                break
            continue
        if step.stop == "tool_use":
            stop_reason = "round_limit"
            messages.append({"role":"user", "content":"Tool round limit reached. Give the best evidence-based summary now."})
            final = llm.step(SYSTEM_PROMPT, messages, [])
            usages.append(final.usage or {})
            messages.append(llm.assistant_message(final))
            answer = final.text
            stop_reason = "round_limit" if final.stop == "end" else final.stop
            break
        stop_reason = step.stop
        answer = step.text
        break
    if not answer and stop_reason == "refusal":
        answer = "I can't help with that request."
    elif not answer and stop_reason == "max_tokens":
        answer = "The response stopped at the model's token limit."
    if successful_tool_count == 0:
        answer = "I could not establish an answer because no successful tool returned FalkorDB evidence."
    memory.record_episode(session_id, question, answer, [item["tool"] for item in trail], sorted(entities))
    return {"answer":answer, "tool_calls":trail, "graph":evidence, "entities":sorted(entities),
            "stop_reason":stop_reason, "usage":usages}

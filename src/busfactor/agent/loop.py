"""Bounded tool loop; all graph facts in an answer must have a returned graph-tool result."""
from __future__ import annotations

from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import json
import logging
import time
import uuid

from busfactor import handover
from busfactor import tools as graph_tools

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
from busfactor.db import get_graph
from .llm import Step
from .memory import Memory, entity_keys, record_episode_if_live
from .prompt import SYSTEM_PROMPT
from .followups import build_followups

MAX_TOOL_RESULT_ROWS = 40
MAX_LIST_ITEMS = 10
MAX_STRING_CHARS = 2000

TOOL_ORDER = ["bus_factor", "bus_factor_component", "departure_impact", "departure_files",
              "orphaned_decisions", "decision_share", "successor", "simulate_departure", "bridges",
              "groups", "decision_trace", "why_not", "drift", "declared_vs_actual", "find_entity",
              "remember_correction", "handover_plan", "mark_unavailable"]
PARAMS = {
    "bus_factor": {"since":"integer", "minCommits":"integer", "minTotal":"integer"},
    "bus_factor_component": {"since":"integer", "minCommits":"integer", "minTotal":"integer", "includeTestResources":"boolean"},
    "departure_impact": {"login":"string", "since":"integer", "minCommits":"integer", "componentPrefix":"string", "includeTestResources":"boolean"},
    "departure_files": {"login":"string", "since":"integer", "componentPrefix":"string", "includeTestResources":"boolean"},
    "orphaned_decisions": {"login":"string", "minConfidence":"string"},
    "decision_share": {"login":"string", "minShare":"number", "minConfidence":"string"},
    "successor": {"login":"string", "component":"string", "since":"integer"},
    "simulate_departure": {"login":"string"}, "bridges": {"limit":"integer"}, "groups": {},
    "decision_trace": {"path":"string", "limit":"integer"}, "why_not": {"slug":"string"},
    "drift": {"minConfidence":"string"},
    "declared_vs_actual": {"since":"integer", "minCommits":"integer"},
    "find_entity": {"text":"string", "limit":"integer"},
    "remember_correction": {"key":"string", "text":"string", "source":"string"},
    "handover_plan": {"login":"string", "component":"string"},
    "mark_unavailable": {"login":"string", "reason":"string"},
}
# Tools that are not in the read-only graph registry describe themselves here.
DESCRIPTIONS = {
    "remember_correction": "Store a user's correction in their memory graph; this does not modify delta.",
    "handover_plan": "Draft a handover plan for one code area if a person leaves: a suggested successor with separate "
                     "evidence (reviews of their PRs, shared files, own commits, area reviews, shared decisions), PRs to "
                     "read, decisions to preserve with sources, and questions for the leaving person. People marked "
                     "unavailable in team memory are skipped.",
    "mark_unavailable": "Record in shared team memory that a person is unavailable for handover work, with the "
                        "reason the user gave. It is an unverified note and never changes delta.",
}
REQUIRED = {"departure_impact":["login"], "departure_files":["login"], "orphaned_decisions":["login"],
            "decision_share":["login"], "successor":["login","component"], "simulate_departure":["login"],
            "decision_trace":["path"], "why_not":["slug"], "remember_correction":["key","text"],
            "handover_plan":["login","component"], "mark_unavailable":["login","reason"]}


def tool_specs() -> list[dict]:
    specs = []
    for name in TOOL_ORDER:
        function = graph_tools.TOOLS.get(name)
        description = function.__doc__ if function else DESCRIPTIONS[name]
        props = {key: {"type": PARAMS[name][key]} for key in graph_tools.LLM_TOOL_PARAMS[name]}
        specs.append({"name": name, "description": description,
                      "input_schema": {"type":"object", "properties":props,
                                       "required":graph_tools.LLM_TOOL_REQUIRED.get(name, []), "additionalProperties":False},
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
        valid = (isinstance(value, bool) if kind == "boolean" else
                 isinstance(value, str) if kind == "string" else
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


def _first_user_message(question: str, today: str, recalled: list[dict], team_recall: list[dict] | None = None) -> str:
    sections = [f"Today is {today}."]
    if recalled:
        labels = {"entity":"Entity", "lastAsked":"Last asked", "earlierQuestions":"Earlier questions",
                  "corrections":"Corrections", "changedSinceLastAsked":"Changes since then"}
        entries = []
        for item in recalled:
            lines = []
            for key, value in item.items():
                if key == "changedSinceLastAsked" and value and item.get("lastAsked"):
                    stamp = datetime.fromtimestamp(int(item["lastAsked"]) / 1000, timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
                    commits = sum(int(change.get("commitCount") or 0) for change in value)
                    prs = sum(int(change.get("prCount") or 0) for change in value)
                    authors = sorted({commit.get("author") for change in value for commit in change.get("commits", []) if commit.get("author")})
                    entity = item.get("entity", "entity")
                    by = ", ".join(authors) or "unknown authors"
                    change_text = f"{commits} new commits by {by}" if commits else f"{prs} new PRs"
                    if commits and prs:
                        change_text += f" and {prs} new PRs"
                    lines.append(f"  Since you last asked about {entity} ({stamp}): {change_text}.")
                    continue
                if key == "lastAsked" and value:
                    stamp = datetime.fromtimestamp(int(value) / 1000, timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
                    lines.append(f"  Last asked: {stamp}")
                    continue
                if value is None or value == [] or value == {}:
                    continue
                rendered = json.dumps(value, ensure_ascii=False, default=str)
                lines.append(f"  {labels.get(key, key)}: {rendered}")
            if lines:
                entries.append("\n".join(lines))
        if entries:
            sections.append("What you remember about this user:\n" + "\n".join(entries))
    if team_recall:
        entries = []
        for item in team_recall:
            provenance = "User-provided claim" if item.get("kind") == "user_claim" else item.get("kind", "team observation")
            entries.append(f"- [{provenance}; {item.get('agent')}]: {item.get('text')} (entity: {item.get('entity')})")
        sections.append("Shared team memory:\n" + "\n".join(entries))
    sections.append(f"Question: {question}")
    return "\n\n".join(sections)


def ask(question: str, user: str, session_id: str | None = None, llm=None, *, memory: Memory | None = None,
        graph=None, max_rounds: int = 8) -> dict:
    request_started = time.perf_counter()
    visitor = str(user)[-8:]
    if llm is None:
        from .llm import create_llm
        llm = create_llm()
    graph = graph or get_graph()
    memory = memory or Memory(user)
    session_id = session_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    from busfactor.team_memory import TeamMemory
    phase_started = time.perf_counter()
    question_keys = []
    try:
        question_keys = entity_keys(graph_tools.find_entity(question).get("graph", {}))
    except Exception:
        pass
    team_recall = TeamMemory().recall(question_keys)
    recalled = memory.recall_for_prompt(question, question_keys, delta_graph=graph)
    LOGGER.info("ask_timing visitor=%s phase=memory_recall ms=%.2f", visitor,
                (time.perf_counter() - phase_started) * 1000)
    messages = [{"role":"user", "content":_first_user_message(question, now.date().isoformat(), recalled,
                                                                  team_recall=team_recall)}]
    evidence = {"nodes": [], "edges": []}
    trail, entities, usages, successful_calls = [], set(), [], []
    successful_tool_count = 0
    stop_reason = "end"
    rounds = 0
    while True:
        available = tool_specs() if rounds < max_rounds else []
        round_started = time.perf_counter()
        step = llm.step(SYSTEM_PROMPT, messages, available)
        LOGGER.info("ask_timing visitor=%s phase=llm_round round=%d ms=%.2f", visitor,
                    rounds + 1, (time.perf_counter() - round_started) * 1000)
        usages.append(step.usage or {})
        messages.append(llm.assistant_message(step))
        if step.stop == "tool_use" and rounds < max_rounds:
            rounds += 1
            batch_started = time.perf_counter()
            def execute_call(call):
                name, call_id, raw = call.get("name", ""), call.get("id", str(uuid.uuid4())), call.get("input", {})
                params, error = _validate(name, raw)
                start = time.perf_counter()
                try:
                    if error: raise ValueError(error)
                    if name == "remember_correction":
                        result = memory.store_correction(**params)
                    elif name == "mark_unavailable":
                        result = memory.mark_unavailable(**params)
                    elif name == "handover_plan":
                        result = handover.plan_tool(**params)
                    else:
                        result = graph_tools.TOOLS[name](**params)
                    elapsed = round((time.perf_counter() - start) * 1000, 2)
                    return {"id":call_id,"name":name,"params":params,"result":result,"elapsed":elapsed}
                except Exception as exc:
                    elapsed = round((time.perf_counter() - start) * 1000, 2)
                    return {"id":call_id,"name":name or "unknown","params":raw,"error":str(exc),"elapsed":elapsed}
            with ThreadPoolExecutor(max_workers=6) as pool:
                completed = list(pool.map(execute_call, step.tool_calls))
            LOGGER.info("ask_timing visitor=%s phase=tool_batch round=%d calls=%d ms=%.2f",
                        visitor, rounds, len(completed), (time.perf_counter() - batch_started) * 1000)
            results = []
            for item in completed:
                if "error" in item:
                    tool_result = {"id":item["id"],"content":item["error"],"is_error":True}
                    results.append(tool_result)
                    trail.append({"tool":item["name"],"label":graph_tools.TOOL_LABELS.get(item["name"], item["name"]),
                                  "params":item["params"],"cypher":"","row_count":0,"ms":item["elapsed"]})
                else:
                    successful_tool_count += 1
                    result = item["result"]
                    rows = result.get("rows", [])
                    successful_calls.append({"tool":item["name"], "params":item["params"], "rows":rows})
                    # The UI shows the same compacted rows the model saw; row_count stays the true total.
                    trail.append({"tool":item["name"],"label":graph_tools.TOOL_LABELS.get(item["name"], item["name"]),"params":item["params"],"cypher":result.get("cypher", ""),
                                  "row_count":len(rows),"rows":_compact_rows(rows),"ms":item["elapsed"]})
                    if len(rows) > MAX_TOOL_RESULT_ROWS:
                        trail[-1]["rows_truncated"] = len(rows) - MAX_TOOL_RESULT_ROWS
                    _merge_graph(evidence, result.get("graph", {}))
                    entities.update(entity_keys(result.get("graph", {})))
                    payload = {"tool":item["name"],"row_count":len(rows),"rows":_compact_rows(rows)}
                    if len(rows) > MAX_TOOL_RESULT_ROWS:
                        payload["truncated"] = len(rows) - MAX_TOOL_RESULT_ROWS
                    tool_result = {"id":item["id"],"content":json.dumps(payload, ensure_ascii=False, default=str)}
                    results.append(tool_result)
                trail[-1]["tool_result_chars"] = _tool_result_chars(tool_result)
            messages.append(llm.tool_results_message(results))
            if rounds >= max_rounds:
                stop_reason = "round_limit"
                messages.append({"role":"user", "content":"Tool round limit reached. Give the best evidence-based summary now."})
                final_started = time.perf_counter()
                final = llm.step(SYSTEM_PROMPT, messages, [])
                LOGGER.info("ask_timing visitor=%s phase=llm_round round=%d final=true ms=%.2f",
                            visitor, rounds + 1, (time.perf_counter() - final_started) * 1000)
                usages.append(final.usage or {})
                messages.append(llm.assistant_message(final))
                answer = final.text
                if final.stop != "end": stop_reason = final.stop
                break
            continue
        if step.stop == "tool_use":
            stop_reason = "round_limit"
            messages.append({"role":"user", "content":"Tool round limit reached. Give the best evidence-based summary now."})
            final_started = time.perf_counter()
            final = llm.step(SYSTEM_PROMPT, messages, [])
            LOGGER.info("ask_timing visitor=%s phase=llm_round round=%d final=true ms=%.2f",
                        visitor, rounds + 1, (time.perf_counter() - final_started) * 1000)
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
    phase_started = time.perf_counter()
    record_episode_if_live(memory, user, session_id, question, answer,
                           [item["tool"] for item in trail], sorted(entities))
    LOGGER.info("ask_timing visitor=%s phase=recording ms=%.2f", visitor,
                (time.perf_counter() - phase_started) * 1000)
    LOGGER.info("ask_timing visitor=%s phase=total ms=%.2f", visitor,
                (time.perf_counter() - request_started) * 1000)
    return {"answer":answer, "tool_calls":trail, "graph":evidence, "entities":sorted(entities),
            "stop_reason":stop_reason, "usage":usages, "memory_recall":recalled,
            "team_memory":team_recall, "followups":build_followups(successful_calls, question=question)}

"""Build complete next questions from structured graph-tool evidence."""
from __future__ import annotations


def _departure(params: dict, rows: list[dict]) -> list[str]:
    login = params.get("login")
    if not login:
        return []
    questions = []
    for row in rows:
        if not row.get("component") or row.get("risk") not in {"NO OTHER AUTHOR", "ONE OTHER AUTHOR"}:
            continue
        person = row.get("name")
        row_login = row.get("login") or login
        person = f"{person} (@{row_login})" if person else row_login
        questions.append(f"Who could take over {row['component']} if {person} left?")
    return questions


def _decision_share(params: dict, rows: list[dict]) -> list[str]:
    return [f"Who else worked on {row['decision']}?" for row in rows if row.get("decision")]


def _simulate(params: dict, rows: list[dict]) -> list[str]:
    login = params.get("login")
    return [f"Who would lose their link to the main collaboration network if {login} left?"] if login and rows and rows[0].get("cutOff") is not None else []


def _trace(params: dict, rows: list[dict]) -> list[str]:
    return [f"Who took part in {row['decisionTitle']}?" for row in rows if row.get("decisionTitle")]


def _why_not(params: dict, rows: list[dict]) -> list[str]:
    return [f"Which files changed since {row['chosenInstead']} was accepted?"
            for row in rows if row.get("chosenInstead") and int(row.get("changesSinceDecision") or 0) > 0]


# One small, reviewable table; each template uses only parameters or returned rows.
FOLLOWUP_TEMPLATES = {
    "departure_impact": _departure,
    "decision_share": _decision_share,
    "simulate_departure": _simulate,
    "decision_trace": _trace,
    "why_not": _why_not,
}


def build_followups(successful_calls: list[dict], limit: int = 4,
                    question: str | None = None) -> list[str]:
    """Choose varied suggestions with one initial suggestion per tool."""
    questions_by_tool = {}
    for call in successful_calls:
        tool = call.get("tool")
        make = FOLLOWUP_TEMPLATES.get(tool)
        if make:
            questions_by_tool.setdefault(tool, []).extend(
                make(call.get("params") or {}, call.get("rows") or []),
            )
    by_tool = list(questions_by_tool.items())

    asked = " ".join((question or "").casefold().split())
    seen = set()
    counts = {}
    suggestions = []
    # Round-robin passes prevent one tool with many rows from filling every chip.
    max_passes = max((len(items) for _, items in by_tool), default=0)
    for index in range(max_passes):
        for tool, items in by_tool:
            if index >= len(items) or counts.get(tool, 0) >= 2:
                continue
            candidate = items[index]
            normalized = " ".join(candidate.casefold().split())
            if normalized == asked or candidate in seen:
                continue
            seen.add(candidate)
            suggestions.append(candidate)
            counts[tool] = counts.get(tool, 0) + 1
            if len(suggestions) >= limit:
                return suggestions
    return suggestions

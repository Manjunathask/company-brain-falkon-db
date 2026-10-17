"""Build complete next questions from structured graph-tool evidence."""
from __future__ import annotations


def _departure(params: dict, rows: list[dict]) -> list[str]:
    login = params.get("login")
    if not login:
        return []
    return [f"Who could take over {row['component']} if {login} left?"
            for row in rows if row.get("component") and row.get("risk") in {"ORPHANED", "AT RISK"}]


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


def build_followups(successful_calls: list[dict], limit: int = 4) -> list[str]:
    questions = []
    seen = set()
    for call in successful_calls:
        make = FOLLOWUP_TEMPLATES.get(call.get("tool"))
        if not make:
            continue
        for question in make(call.get("params") or {}, call.get("rows") or []):
            if question not in seen:
                seen.add(question)
                questions.append(question)
                if len(questions) >= limit:
                    return questions
    return questions

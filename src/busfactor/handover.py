"""Build a sourced handover packet for one leaving person and one code area.

Every fact comes from a Cypher query in queries/: 18_handover_candidates, 18b_handover_reading,
18c_handover_decisions and 06b_departure_files read the delta graph; 16f/16h read shared team memory
(availability notes and saved packets), joined to delta by login in Python because Cypher cannot cross
graphs. This module only orders rows, fills question templates and formats the result. No LLM is involved.
"""
from __future__ import annotations

from datetime import datetime, timezone

from busfactor import tools as graph_tools
from busfactor.db import get_graph, load_query
from busfactor.team_memory import TeamMemory

GITHUB = "https://github.com/delta-io/delta"
CAVEAT = ("Suggested from public GitHub activity. Confirm availability, interest and readiness "
          "with the people involved.")
GRAPH_QUERIES = ["18_handover_candidates", "18b_handover_reading", "18c_handover_decisions", "06b_departure_files"]
MEMORY_QUERIES = ["16f_team_availability", "16h_team_last_handover", "18e_handover_activity_since"]
MAX_CANDIDATES = 5
MAX_QUESTIONS = 6


def _rows(graph, name: str, params: dict) -> list[dict]:
    result = graph.ro_query(load_query(name), params)
    columns = [header[1] for header in result.header]
    return [dict(zip(columns, row)) for row in result.result_set]


def _plural(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


def _date(ts: int | None) -> str:
    return datetime.fromtimestamp(ts / 1000, timezone.utc).strftime("%d %b %Y") if ts else "an unknown date"


def why_sentence(candidate: dict, leaving: str) -> str:
    """One plain sentence built only from the candidate's evidence columns."""
    parts = []
    if candidate["reviewedTheirPRs"]:
        parts.append(f"reviewed {candidate['reviewedTheirPRs']} of {leaving}'s "
                     f"{_plural(candidate['theirPRCount'], 'PR')} here")
    if candidate["sharedFiles"]:
        parts.append(f"edited {candidate['sharedFiles']} of the {candidate['outOf']} files {leaving} changed")
    parts.append(f"{_plural(candidate['areaCommits'], 'commit')} of their own here" if candidate["areaCommits"]
                 else "no commits of their own here yet")
    if candidate["areaReviews"] > candidate["reviewedTheirPRs"]:
        parts.append(f"{_plural(candidate['areaReviews'], 'PR')} reviewed in this area in total")
    if candidate["sharedDecisions"]:
        parts.append("took part in " + ", ".join(candidate["sharedDecisions"]))
    text = "; ".join(parts)
    return text[0].upper() + text[1:] + "."


def questions(leaving: str, solo_paths: list[str], decisions: list[dict], reading: list[dict],
              candidate: dict | None) -> list[dict]:
    """Questions for the leaving person, each tied to the query row it came from."""
    asked: list[dict] = []
    for path in solo_paths[:2]:
        asked.append({"text": f"What should the next owner know before changing {path}?",
                      "from": "06b_departure_files: only they edited this file in the last 12 months"})
    for decision in decisions:
        if decision["leavingParticipated"] and decision["otherActiveCount"] == 0:
            asked.append({"text": f"Which constraints from {decision['title']} must be kept?",
                          "from": "18c_handover_decisions: no other active participant"})
    for pr in reading:
        links = pr.get("decisions") or []
        if links and all(link.get("confidence") != "high" for link in links):
            asked.append({"text": f"Was PR #{pr['number']} part of {links[0]['title']}? (title-keyword guess)",
                          "from": "18b_handover_reading: the only decision link is a title match"})
    if candidate:
        for path in [p for p in candidate["toLearn"] if p not in solo_paths[:2]][:2]:
            asked.append({"text": f"Can you walk {candidate['login']} through {path}?",
                          "from": "18_handover_candidates: only they edited it, and the candidate never has"})
    seen, unique = set(), []
    for item in asked:
        if item["text"] not in seen:
            seen.add(item["text"])
            unique.append(item)
    return unique[:MAX_QUESTIONS]


def _changed(graph, component: str, previous: dict | None, top: dict | None, skipped: list[dict]) -> dict | None:
    """Compare with the last saved packet: who it suggested, and why the suggestion differs now."""
    if not previous:
        return None
    before, now = previous.get("candidate"), top["login"] if top else None
    reasons = []
    note = next((item for item in skipped if item["login"] == before), None)
    if before and before != now and note:
        reasons.append(f"{before} was marked unavailable on {_date(note['ts'])}"
                       f"{': ' + note['reason'] if note.get('reason') else ''} (unverified note)")
    activity = _rows(graph, "18e_handover_activity_since", {"component": component, "since": previous["ts"]})[0]
    if activity["commits"] or activity["prs"]:
        reasons.append(f"{_plural(activity['commits'], 'commit')} and {_plural(activity['prs'], 'PR')} "
                       "landed in this area since then")
    return {"previousDate": _date(previous["ts"]), "previousTs": previous["ts"], "previousCandidate": before,
            "candidate": now, "same": before == now, "reasons": reasons}


def build_packet(login: str, component: str, *, name: str | None = None, graph=None, team=None,
                 since: int | None = None, include_graph: bool = True) -> dict:
    graph = graph or get_graph()
    team = team or TeamMemory()
    since = since or graph_tools.DEFAULTS["since"]
    leaving = name or login
    notes = team.availability()
    unavailable = {person: note for person, note in notes.items() if note.get("status") == "unavailable"}
    rows = _rows(graph, "18_handover_candidates", {
        "login": login, "component": component, "since": since,
        "exclude": sorted(unavailable), "limit": MAX_CANDIDATES + len(unavailable)})
    candidates = [row for row in rows if not row["skipped"]][:MAX_CANDIDATES]
    skipped = [{"login": row["login"], "name": row["name"], "status": "unavailable",
                "reason": unavailable[row["login"]].get("reason"), "ts": unavailable[row["login"]].get("ts"),
                "source": unavailable[row["login"]].get("source"), "label": "Unverified availability note"}
               for row in rows if row["skipped"]]
    top = candidates[0] if candidates else None
    reading = _rows(graph, "18b_handover_reading", {"login": login, "component": component, "since": since, "limit": 3})
    preserve = _rows(graph, "18c_handover_decisions", {"login": login, "component": component})
    files = _rows(graph, "06b_departure_files", {"login": login, "since": since, "componentPrefix": component,
                                                  "includeTestResources": False})
    solo = next((row for row in files if row["component"] == component), None)
    solo_paths = (solo or {}).get("examplePaths") or []
    packet = {
        "login": login, "name": leaving, "component": component,
        "successor": {**top, "why": why_sentence(top, leaving)} if top else None,
        "candidates": candidates, "skipped": skipped,
        "read": reading, "preserve": preserve,
        "soloFiles": {"count": (solo or {}).get("orphanedFiles", 0), "examples": solo_paths},
        "ask": questions(leaving, solo_paths, preserve, reading, top),
        "changed": _changed(graph, component, team.last_handover(login, component), top, skipped),
        "caveat": CAVEAT, "queries": GRAPH_QUERIES + MEMORY_QUERIES,
        "draftedOn": datetime.now(timezone.utc).strftime("%d %b %Y"),
    }
    packet["markdown"] = to_markdown(packet)
    packet["graph"] = graph_tools._graph_for("18_handover", [], graph, {
        "login": login, "component": component, "prs": [row["number"] for row in reading],
        "candidates": [row["login"] for row in candidates]}) if include_graph else {"nodes": [], "edges": []}
    return packet


def _decision_line(decision: dict) -> str:
    title = (f"[{decision['title']}]({GITHUB}/blob/master/{decision['rfcPath']})" if decision.get("rfcPath")
             else decision["title"])
    issue = f" · [issue #{decision['issue']}]({GITHUB}/issues/{decision['issue']})" if decision.get("issue") else ""
    line = (f"- {title} ({decision.get('status') or 'unknown'}){issue}: {decision['explicitPRs']} explicitly linked "
            f"PRs here, {decision['titleMatchPRs']} title matches (keyword guesses)")
    if decision.get("supersession"):
        line += f"; {decision['supersession']}"
    if decision.get("rationale"):
        quote = decision["rationale"].replace("\n", "\n  > ")
        line += f"\n  Stated reason ({decision.get('rationaleSource')}):\n  > {quote}"
    return line


def to_markdown(packet: dict) -> str:
    """The packet as a checklist that can be pasted into a GitHub issue."""
    leaving, login = packet["name"], packet["login"]
    lines = [f"# Handover: {packet['component']}", "",
             f"Leaving: {leaving} (@{login}) · drafted {packet['draftedOn']}", ""]
    if packet.get("changed"):
        changed = packet["changed"]
        summary = (f"Same suggestion as the packet saved on {changed['previousDate']}." if changed["same"] else
                   f"The packet saved on {changed['previousDate']} suggested {changed['previousCandidate']}; "
                   f"now {changed['candidate'] or 'nobody'}.")
        reasons = f" Why: {'; '.join(changed['reasons'])}." if changed["reasons"] else ""
        lines += [f"**What changed:** {summary}{reasons}", ""]
    lines += ["## Suggested successor", ""]
    successor = packet.get("successor")
    if successor:
        lines += [f"**{successor['login']}**: {successor['why']}", "",
                  f"| Candidate | Reviewed {login}'s PRs here | Shared files | Own commits here | PRs reviewed here | Shared decisions |",
                  "|---|---|---|---|---|---|"]
        for row in packet["candidates"]:
            lines.append(f"| {row['login']} | {row['reviewedTheirPRs']} of {row['theirPRCount']} | "
                         f"{row['sharedFiles']} of {row['outOf']} | {row['areaCommits']} | {row['areaReviews']} | "
                         f"{', '.join(row['sharedDecisions']) or '—'} |")
        if successor["toLearn"]:
            lines += ["", f"Not touched by {successor['login']} yet: " + ", ".join(f"`{p}`" for p in successor["toLearn"])]
    else:
        lines.append(f"No active author or reviewer of this area was found besides {leaving}.")
    for item in packet["skipped"]:
        lines.append(f"- Skipped {item['login']}: marked unavailable on {_date(item['ts'])}"
                     f"{' (' + item['reason'] + ')' if item.get('reason') else ''}; unverified note.")
    lines += ["", "## Read these first", ""]
    for pr in packet["read"]:
        decisions = ", ".join(f"{d['title']} ({'explicit' if d['confidence'] == 'high' else 'title match'})"
                              for d in pr.get("decisions") or [])
        lines.append(f"- [ ] [#{pr['number']} {pr['title']}]({GITHUB}/pull/{pr['number']}): "
                     f"{_plural(pr['filesHere'], 'file')} here" + (f" · decisions: {decisions}" if decisions else ""))
    if not packet["read"]:
        lines.append(f"- No recent PRs by {leaving} in this area.")
    lines += ["", "## Decisions to preserve", ""]
    lines += [_decision_line(d) for d in packet["preserve"]] or ["- No RFC decision is linked to this area's PRs."]
    lines += ["", f"## Questions for {leaving}", ""]
    lines += [f"{index}. {item['text']}" for index, item in enumerate(packet["ask"], 1)] or ["- None generated."]
    lines += ["", f"> {packet['caveat']}", "",
              f"_Generated by Bus Factor from FalkorDB queries {', '.join(packet['queries'])} on {packet['draftedOn']}._"]
    return "\n".join(lines) + "\n"


def save_packet(login: str, component: str, candidate: str | None, *, agent: str, source: str, team=None) -> dict:
    return (team or TeamMemory()).write_handover(agent=agent, login=login, component=component,
                                                  candidate=candidate, source=source)


def mark_availability(login: str, status: str, reason: str, *, agent: str, source: str, team=None) -> dict:
    if status not in {"unavailable", "available"}:
        raise ValueError("status must be 'unavailable' or 'available'")
    return (team or TeamMemory()).write_availability(agent=agent, login=login, status=status,
                                                      reason=reason.strip()[:200], source=source)


def plan_tool(login: str, component: str) -> dict:
    """Agent tool: the packet without markdown, as one row, plus its evidence graph."""
    packet = build_packet(login, component)
    row = {key: value for key, value in packet.items() if key not in {"markdown", "graph", "queries"}}
    cypher = "\n\n".join(f"// {name}.cypher\n{load_query(name)}" for name in GRAPH_QUERIES)
    return {"tool": "handover_plan", "params": {"login": login, "component": component},
            "cypher": cypher, "rows": [row], "graph": packet["graph"]}

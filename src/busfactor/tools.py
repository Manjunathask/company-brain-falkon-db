"""Plain, inspectable registry of FalkorDB-backed agent tools."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import re
import time
from difflib import SequenceMatcher

from busfactor.db import ROOT, get_graph, load_query
from busfactor.graphjson import node_dict as _node, rel_dict as _rel
from busfactor.whatif import simulate_departure as _simulate_departure

DEFAULTS = {
    "since": int((datetime.now(timezone.utc) - timedelta(days=365)).timestamp() * 1000),
    "minCommits": 2,
    "minTotal": 5,
    "minConfidence": "low",
    "minShare": 0.3,
    "driftMinConfidence": "high",
    "includeTestResources": False,
}
TOOL_LABELS = {
    "bus_factor": "Measured bus factor by module",
    "bus_factor_component": "Measured bus factor by component",
    "departure_impact": "Checked which components would be exposed",
    "departure_files": "Checked which files would lose recent editors",
    "orphaned_decisions": "Checked decisions with no active participant left",
    "decision_share": "Checked who opened implementation pull requests",
    "successor": "Found people with overlapping recent work",
    "simulate_departure": "Simulated the departure on a copy of the graph",
    "bridges": "Ranked people who connect collaboration groups",
    "groups": "Measured collaboration groups",
    "decision_trace": "Traced files through commits, pull requests, and decisions",
    "why_not": "Traced why a rejected decision was replaced",
    "drift": "Measured code changes since accepted decisions",
    "declared_vs_actual": "Compared declared owners with recent contributors",
    "find_entity": "Found matching graph entities",
    "remember_correction": "Saved a correction to memory",
    "handover_plan": "Drafted a handover plan from graph evidence",
    "mark_unavailable": "Saved an availability note to team memory",
}
GRAPH_KEY_MAP = {
    "05_bus_factor": {"modules": "module", "people": "topExpert"},
    "05b_bus_factor_component": {"components": "component", "people": "topExpert"},
    "06_departure_impact": {"people": "login", "components": "component"},
    "06b_departure_files": {"people": "login", "components": "component", "files": "examplePaths"},
    "07_orphaned_decisions": {"people": "login", "decisions": "decision"},
    "07b_decision_share": {"people": "login", "decisions": "decision"},
    "08_successor": {"people": "successor", "components": "component"},
    "09_bridges": {"people": "person"},
    "09b_groups": {},
    "10b_why_not": {"decisions": "rejected"},
    "11_drift": {"decisions": "decision"},
    "12_declared_vs_actual": {"modules": "module"},
    "13_find_entity": {"people": "key", "modules": "key", "components": "key", "decisions": "key", "files": "key"},
}

# Entity validation is deliberately separate from tool schemas and main queries.
INPUT_CHECKS = {
    "departure_impact": {"login": "active_person", "componentPrefix": "component_prefix"},
    "departure_files": {"login": "active_person", "componentPrefix": "component_prefix"},
    "orphaned_decisions": {"login": "active_person"},
    "decision_share": {"login": "active_person"},
    "successor": {"login": "active_person", "component": "component"},
    "simulate_departure": {"login": "active_person"},
    "handover_plan": {"login": "active_person", "component": "component"},
    "mark_unavailable": {"login": "active_person"},
    "why_not": {"slug": "decision"},
    "decision_trace": {"path": "file"},
    "remember_correction": {"key": "entity_key"},
}
CHECK_QUERIES = {
    "active_person": ("17c_active_person", "login"),
    "person": ("17e_person_status", "login"),
    "component": ("17d_component_exists", "component"),
    "component_prefix": ("17f_component_prefix", "prefix"),
    "decision": ("17g_decision_exists", "slug"),
    "file": ("17h_file_exists", "path"),
    "module": ("17i_module_exists", "name"),
}
EMPTY_THRESHOLDS = {
    "bus_factor": "modules with 5+ qualifying commits, counting authors with 2+ non-bulk commits on current files in the last 12 months",
    "bus_factor_component": "areas with 5+ qualifying commits, counting authors with 2+ non-bulk commits on current files in the last 12 months",
    "departure_impact": "areas where this person made 2+ non-bulk commits on current files in the last 12 months",
    "departure_files": "current files edited by this person in non-bulk commits in the last 12 months, with no other active non-bot recent editor",
    "orphaned_decisions": "decisions where this person is the only active participant at the requested confidence",
    "decision_share": "decisions where this person opened at least the requested share of implementing PRs at the requested confidence",
    "successor": "active non-bot people sharing current files edited in non-bulk commits in this area in the last 12 months",
    "simulate_departure": "an active non-bot person in the collaboration graph",
    "bridges": "active non-bot people ranked by betweenness in the collaboration graph",
    "groups": "active collaboration groups in the graph",
    "decision_trace": "a file linked through a commit and PR to a decision and its tracking issue",
    "why_not": "a rejected decision with a SUPERSEDED_BY edge",
    "drift": "accepted decisions with qualifying implementation links and later edits to their files",
    "declared_vs_actual": "modules with declared owners or qualifying recent authors",
    "handover_plan": "eligible active authors or reviewers in this area, or recent PRs by the leaving person for the reading list",
    "remember_correction": "a saved correction for the specified graph entity",
    "mark_unavailable": "a saved availability note for the specified active non-bot person",
}
# A search that finds nothing has no threshold and says nothing about risk, so it gets its own note.
EMPTY_NOTES = {
    "find_entity": "No person, code area, module, decision or file in the graph matches this text. "
                   "Try part of the name or login.",
}
BLOCKED_OUTCOMES = {"unknown_entity", "inactive_person"}
UNKNOWN_NOTE = ("Nothing else was run. Use one of the suggestions or ask the user which they meant; "
                "this result says nothing about risk.")


def run_check_query(name: str, params: dict | None = None, *, graph=None) -> list[dict]:
    """Single read-only seam for name checks, suggestions and the reply catalogue."""
    result = (graph if graph is not None else get_graph()).ro_query(load_query(name), params or {})
    columns = [header[1] for header in result.header]
    return [dict(zip(columns, row)) for row in result.result_set]


def _suggestions(value: str, kind: str, run) -> list[dict]:
    texts = [value, re.sub(r"[-_. ]", "", value)]
    texts.extend(token for token in re.split(r"[-_/\. ]+", value) if len(token) >= 3)
    if kind in {"component", "file"} and "/" in value:
        parent, last = value.rsplit("/", 1)
        texts.extend([parent + "/", last])
    candidates = {}
    for text in dict.fromkeys(texts):
        if not text:
            continue
        # Search broadly before ranking: a five-hit prefix search can hide the intended area.
        for row in run("13_find_entity", {"text": text, "limit": 10000}):
            if row["kind"] == kind:
                candidates[row["key"]] = {"key": row["key"], "label": row["label"]}
    return sorted(candidates.values(), key=lambda row: (
        -SequenceMatcher(None, value.lower(), row["key"].lower()).ratio(), row["key"]))[:5]


def resolve_inputs(name: str, params: dict, *, graph=None) -> dict | None:
    """Check every supplied entity argument; return metadata, blocking the whole call on any miss."""
    checks = []
    for arg, check_kind in INPUT_CHECKS.get(name, {}).items():
        if arg not in params or (check_kind == "component_prefix" and not params[arg]):
            continue
        value = params[arg]
        lookup = value
        if check_kind == "entity_key":
            check_kind, separator, lookup = value.partition(":")
            if not separator or check_kind not in {"person", "component", "module", "decision"}:
                raise ValueError("key must use person:, component:, module:, or decision:")
        kind = {"active_person": "person", "component_prefix": "component"}.get(check_kind, check_kind)
        queries = []

        def run(query_name, query_params):
            started = time.perf_counter()
            rows = run_check_query(query_name, query_params, graph=graph)
            queries.append({"name": query_name, "params": query_params,
                            "ms": round((time.perf_counter() - started) * 1000, 2),
                            "cypher": load_query(query_name)})
            return rows

        query_name, parameter = CHECK_QUERIES[check_kind]
        rows = run(query_name, {parameter: lookup})
        status = "ok" if rows else "not_in_graph"
        if check_kind == "component_prefix":
            status = "ok" if rows and rows[0]["count"] > 0 else "not_in_graph"
        if check_kind == "active_person" and not rows:
            rows = run("17e_person_status", {"login": lookup})
            status = "inactive" if rows else "not_in_graph"
        check = {"arg": arg, "value": value, "kind": kind, "status": status, "suggestions": []}
        if rows and check_kind in {"active_person", "person"}:
            check.update({key: rows[0].get(key) for key in ("name", "bot", "lastSeen") if key in rows[0]})
            stamp = check.get("lastSeen")
            if isinstance(stamp, (int, float)):
                check["lastSeen"] = datetime.fromtimestamp(stamp / 1000, timezone.utc).date().isoformat()
        if status == "not_in_graph":
            check["suggestions"] = _suggestions(lookup, kind, run)
        check["queries"] = queries
        check["ms"] = round(sum(query["ms"] for query in queries), 2)
        checks.append(check)
    if not checks:
        return None
    unknown = any(check["status"] == "not_in_graph" for check in checks)
    inactive = [check for check in checks if check["status"] == "inactive"]
    outcome = "unknown_entity" if unknown else "inactive_person" if inactive else "ok"
    note = UNKNOWN_NOTE if unknown else ""
    if inactive:
        people = "; ".join(f"{check.get('name') or check['value']} ({check['value']}), last seen "
                           f"{check.get('lastSeen') or 'on an unknown date'}"
                           + (", marked as a bot" if check.get("bot") else "") for check in inactive)
        note = (note + " " if note else "") + (
            f"{people}. Departure tools only cover non-bot people active in the last 12 months. Nothing else was run.")
    return {"outcome": outcome, "checks": checks, "note": note}


def run_tool(name: str, params: dict, *, graph=None, function=None) -> dict:
    """Shared agent/API/CLI dispatch: resolve first, then label the returned evidence."""
    resolution = resolve_inputs(name, params, graph=graph) or {"outcome": "ok", "note": ""}
    if resolution["outcome"] in BLOCKED_OUTCOMES:
        return {"tool": name, "params": params, "rows": [], "row_count": 0, "cypher": "",
                "graph": {"nodes": [], "edges": []}, **resolution}
    result = (function or TOOLS[name])(**params)
    rows = result.get("rows", [])
    empty = not rows
    if name == "handover_plan" and rows:
        empty = all(not row.get("candidates") and not row.get("read") for row in rows)
    if empty:
        resolution.update(outcome="no_qualifying_evidence", note=EMPTY_NOTES.get(name) or (
            f"This query requires {EMPTY_THRESHOLDS[name]}. "
            "The graph holds no qualifying evidence for this; do not read it as nothing being at risk."))
    return {**result, **resolution, "row_count": len(rows)}

def _params_for_graph(rows: list[dict], mapping: dict[str, str]) -> dict[str, list]:
    keys = {k: [] for k in ("people", "components", "modules", "decisions", "files", "prs", "issues")}
    for row in rows:
        for target, column in mapping.items():
            value = row.get(column)
            if value is None:
                continue
            values = value if isinstance(value, list) else [value]
            if target == "people" and isinstance(value, dict):
                value = value.get("key")
            if target == "people" and column == "key" and not str(value).startswith("person:"):
                continue
            if target == "modules" and column == "key" and not str(value).startswith("module:"):
                continue
            if target == "components" and column == "key" and not str(value).startswith("component:"):
                continue
            if target == "decisions" and column == "key" and not str(value).startswith("decision:"):
                continue
            if target == "files" and column == "key" and not str(value).startswith("file:"):
                continue
            if target == "people" and column == "key": value = str(value)[7:]
            if target == "modules" and column == "key": value = str(value)[7:]
            if target == "components" and column == "key": value = str(value)[10:]
            if target == "decisions" and column == "key": value = str(value)[9:]
            if target == "files" and column == "key": value = str(value)[5:]
            for item in values:
                if item is not None and item not in keys[target]: keys[target].append(item)
    return keys

def _graph_for(name: str, rows: list[dict], graph=None, main_params: dict | None = None) -> dict:
    if name == "10_decision_trace":
        nodes, edges = {}, {}
        for row in rows:
            path = row.get("p")
            if path is None: continue
            path_nodes = getattr(path, "nodes", [])
            path_nodes = path_nodes() if callable(path_nodes) else path_nodes
            path_rels = getattr(path, "relationships", getattr(path, "rels", getattr(path, "edges", [])))
            path_rels = path_rels() if callable(path_rels) else path_rels
            for item in path_nodes:
                n = _node(item)
                if n: nodes[n["id"]] = n
            for item in path_rels:
                e = _rel(item)
                if e: edges[(e["source"],e["target"],e["type"])] = e
        return {"nodes": list(nodes.values()), "edges": list(edges.values())}
    query = load_query(name + "_graph")
    params = _params_for_graph(rows, GRAPH_KEY_MAP.get(name, {}))
    params.update(main_params or {})
    if name in {"05_bus_factor", "05b_bus_factor_component"}:
        key = "module" if name == "05_bus_factor" else "component"
        params["areas"] = [{"name": row[key], "countedExperts": row["countedExperts"]} for row in rows if row.get(key) is not None]
    elif name == "06_departure_impact":
        params["areas"] = [{"name": row["component"], "remaining": row["remaining"],
                            "reviewers": row["reviewers"]} for row in rows]
    elif name == "07_orphaned_decisions":
        params["decisions"] = [row["decision"] for row in rows]
    elif name == "07b_decision_share":
        params["decisions"] = [row["decision"] for row in rows]
    elif name == "08_successor":
        params["successors"] = [row["successor"] for row in rows]
    elif name == "11_drift":
        params["decisions"] = [row["decision"] for row in rows]
    elif name == "12_declared_vs_actual":
        params["areas"] = [{"name": row["module"], "actualTop3": row["actualTop3"]} for row in rows]
        params["modules"] = [row["module"] for row in rows]
    elif name == "13_find_entity":
        for row in rows:
            category = {"person":"people", "module":"modules", "component":"components", "decision":"decisions", "file":"files"}.get(row.get("kind"))
            if category and row.get("key") not in params[category]: params[category].append(row["key"])
    if graph is None: graph = get_graph()
    result = graph.ro_query(query, params)
    columns = [header[1] for header in result.header]
    nodes, edges = {}, {}
    for record in result.result_set:
        item = dict(zip(columns, record))
        path = item.get("p")
        if path is not None:
            path_nodes = getattr(path, "nodes", [])
            path_nodes = path_nodes() if callable(path_nodes) else path_nodes
            path_rels = getattr(path, "edges", [])
            path_rels = path_rels() if callable(path_rels) else path_rels
            for raw_node in path_nodes:
                node = _node(raw_node)
                if node: nodes[node["id"]] = node
            for raw_edge in path_rels:
                edge = _rel(raw_edge)
                if edge: edges[(edge["source"],edge["target"],edge["type"])] = edge
            continue
        for column in ("node", "n", "m"):
            node = _node(item.get(column))
            if node: nodes[node["id"]] = node
        edge = _rel(item.get("r"))
        if edge: edges[(edge["source"],edge["target"],edge["type"])] = edge
    return {"nodes": list(nodes.values()), "edges": list(edges.values())}

def _run(name: str, params: dict, *, graph=None, include_graph: bool = True) -> dict:
    graph = graph or get_graph()
    query = load_query(name)
    result = graph.ro_query(query, params)
    columns = [header[1] for header in result.header]
    rows = [dict(zip(columns, row)) for row in result.result_set]
    return {"tool": {"05_bus_factor":"bus_factor","05b_bus_factor_component":"bus_factor_component","06_departure_impact":"departure_impact","06b_departure_files":"departure_files","07_orphaned_decisions":"orphaned_decisions","07b_decision_share":"decision_share","08_successor":"successor","09_bridges":"bridges","09b_groups":"groups","10_decision_trace":"decision_trace","10b_why_not":"why_not","11_drift":"drift","12_declared_vs_actual":"declared_vs_actual","13_find_entity":"find_entity"}.get(name, name), "params": params, "cypher": query, "rows": rows, "graph": _graph_for(name, rows, graph, params) if include_graph else {"nodes": [], "edges": []}}

def bus_factor(since: int | None = None, minCommits: int | None = None, minTotal: int | None = None) -> dict:
    """Report module bus factors from recent non-bot commit expertise."""
    return _run("05_bus_factor", {**DEFAULTS, "since": since or DEFAULTS["since"], "minCommits": minCommits or DEFAULTS["minCommits"], "minTotal": minTotal or DEFAULTS["minTotal"]})

def bus_factor_component(since: int | None = None, minCommits: int | None = None, minTotal: int | None = None,
                         includeTestResources: bool = False, *, _include_graph: bool = True) -> dict:
    """Report the number of recent non-bot experts needed to cover half of each Component's commits."""
    return _run("05b_bus_factor_component", {**DEFAULTS, "since": since or DEFAULTS["since"], "minCommits": minCommits or DEFAULTS["minCommits"], "minTotal": minTotal or DEFAULTS["minTotal"], "includeTestResources": includeTestResources}, include_graph=_include_graph)

def departure_impact(login: str, since: int | None = None, minCommits: int | None = None,
                     componentPrefix: str = "", includeTestResources: bool = False) -> dict:
    """Show areas with qualifying recent authorship, remaining recent authors, and separate active reviewers."""
    return _run("06_departure_impact", {"login":login,"since":since or DEFAULTS["since"],"minCommits":minCommits or DEFAULTS["minCommits"],"componentPrefix":componentPrefix,"includeTestResources":includeTestResources})

def departure_files(login: str, since: int | None = None, componentPrefix: str = "",
                    includeTestResources: bool = False) -> dict:
    """Find recent files touched by this person that no other active non-bot person edited."""
    return _run("06b_departure_files", {"login":login,"since":since or DEFAULTS["since"],"componentPrefix":componentPrefix,"includeTestResources":includeTestResources})

def orphaned_decisions(login: str, minConfidence: str | None = None) -> dict:
    """Find decisions where this person's participation is the only active participation at the chosen confidence."""
    return _run("07_orphaned_decisions", {"login":login,"minConfidence":minConfidence or DEFAULTS["minConfidence"]})

def decision_share(login: str, minShare: float | None = None, minConfidence: str | None = None) -> dict:
    """Find decisions where this person opened at least the requested share of implementing PRs, and list active co-openers."""
    return _run("07b_decision_share", {"login":login,"minShare":DEFAULTS["minShare"] if minShare is None else minShare,"minConfidence":minConfidence or DEFAULTS["minConfidence"]})

def successor(login: str, component: str, since: int | None = None) -> dict:
    """Rank active non-bot successors for a Component by shared recent files, then component commit expertise."""
    return _run("08_successor", {"login":login,"component":component,"since":since or DEFAULTS["since"]})

def bridges(limit: int = 10) -> dict:
    """Rank active people who connect collaboration groups using FalkorDB betweenness centrality."""
    return _run("09_bridges", {"limit":limit})

def groups() -> dict:
    """Summarize active collaboration components, including the largest and non-singleton group counts."""
    return _run("09b_groups", {})

def simulate_departure(login: str) -> dict:
    """Copy the graph, remove a person's Active label there, and report centrality and collaboration splits without changing delta."""
    return _simulate_departure(login)

def decision_trace(path: str, limit: int = 5) -> dict:
    """Trace a file through commits, pull requests, decisions, and RFC issues with confidence and evidence source."""
    return _run("10_decision_trace", {"path":path,"limit":limit})

def why_not(slug: str) -> dict:
    """Explain why a rejected decision was superseded, including its replacement and people to ask."""
    return _run("10b_why_not", {"slug":slug})

def drift(minConfidence: str | None = None) -> dict:
    """Measure edits made after accepted decisions; by default only high-confidence implementation links count."""
    return _run("11_drift", {"minConfidence":minConfidence or DEFAULTS["driftMinConfidence"]})

def declared_vs_actual(since: int | None = None, minCommits: int | None = None) -> dict:
    """Compare module CODEOWNERS declarations with the top three recent non-bot commit experts."""
    return _run("12_declared_vs_actual", {"since":since or DEFAULTS["since"],"minCommits":minCommits or DEFAULTS["minCommits"]})

def find_entity(text: str, limit: int = 20) -> dict:
    """Resolve free text to people, modules, Components, decisions, or file paths ending in the supplied text."""
    return _run("13_find_entity", {"text":text,"limit":limit})

TOOLS = {"bus_factor":bus_factor,"bus_factor_component":bus_factor_component,"departure_impact":departure_impact,"departure_files":departure_files,"orphaned_decisions":orphaned_decisions,"decision_share":decision_share,"successor":successor,"bridges":bridges,"groups":groups,"simulate_departure":simulate_departure,"decision_trace":decision_trace,"why_not":why_not,"drift":drift,"declared_vs_actual":declared_vs_actual,"find_entity":find_entity}

# Only expose arguments that change what question a graph tool answers. Tuning
# arguments remain in the Python functions for the CLI and direct API callers.
LLM_TOOL_PARAMS = {
    "bus_factor": [],
    "bus_factor_component": [],
    "departure_impact": ["login", "componentPrefix"],
    "departure_files": ["login", "componentPrefix"],
    "orphaned_decisions": ["login", "minConfidence"],
    "decision_share": ["login", "minConfidence"],
    "successor": ["login", "component"],
    "simulate_departure": ["login"],
    "bridges": ["limit"],
    "groups": [],
    "decision_trace": ["path"],
    "why_not": ["slug"],
    "drift": ["minConfidence"],
    "declared_vs_actual": [],
    "find_entity": ["text"],
    "remember_correction": ["key", "text"],
    "handover_plan": ["login", "component"],
    "mark_unavailable": ["login", "reason"],
}
LLM_TOOL_REQUIRED = {
    "departure_impact": ["login"],
    "departure_files": ["login"],
    "orphaned_decisions": ["login"],
    "decision_share": ["login"],
    "successor": ["login", "component"],
    "simulate_departure": ["login"],
    "bridges": ["limit"],
    "decision_trace": ["path"],
    "why_not": ["slug"],
    "remember_correction": ["key", "text"],
    "handover_plan": ["login", "component"],
    "mark_unavailable": ["login", "reason"],
}

def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Bus Factor graph tool")
    parser.add_argument("tool", choices=TOOLS)
    parser.add_argument("--login"); parser.add_argument("--component"); parser.add_argument("--path"); parser.add_argument("--slug"); parser.add_argument("--text")
    parser.add_argument("--since", type=int); parser.add_argument("--minCommits", type=int); parser.add_argument("--minTotal", type=int); parser.add_argument("--minConfidence"); parser.add_argument("--minShare", type=float); parser.add_argument("--limit", type=int); parser.add_argument("--componentPrefix", default=""); parser.add_argument("--includeTestResources", action="store_true")
    args = parser.parse_args(); values = vars(args); name = args.tool; tool = TOOLS[name]
    values.pop("tool"); values = {k:v for k,v in values.items() if v is not None}
    import inspect
    signature = inspect.signature(tool)
    accepted = {k:v for k,v in values.items() if k in signature.parameters}
    result = run_tool(name, accepted)
    print(f"outcome: {result['outcome']}")
    if result.get("note"):
        print(result["note"])
    for check in result.get("checks", []):
        print(json.dumps(check, ensure_ascii=False))
    rows = result["rows"]
    if rows:
        columns = list(rows[0])
        rendered = [[str(row.get(column, "")) for column in columns] for row in rows]
        widths = [max(len(column), *(len(row[index]) for row in rendered)) for index, column in enumerate(columns)]
        print(" | ".join(column.ljust(widths[index]) for index, column in enumerate(columns)))
        print("-+-".join("-" * width for width in widths))
        for row in rendered:
            print(" | ".join(value.ljust(widths[index]) for index, value in enumerate(row)))
    else:
        print("(no rows)")
    print(f"graph: {len(result['graph']['nodes'])} nodes, {len(result['graph']['edges'])} edges")

if __name__ == "__main__": main()

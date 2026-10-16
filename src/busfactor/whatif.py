"""Run departure what-ifs on a disposable native copy of the FalkorDB graph."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import os
import time
import uuid
from threading import Lock

from busfactor.db import get_client, load_query
from busfactor.graphjson import node_dict, rel_dict

_COPY_LOCK = Lock()


def _read_rows(graph, query_name: str, params: dict | None = None):
    """Run a named read-only query against the temporary graph."""
    return graph.ro_query(load_query(query_name), params or {}).result_set


def simulate_departure(login: str) -> dict:
    """Copy the graph, remove a person's Active label on the copy, and measure the collaboration impact."""
    client = get_client()
    source_name = os.getenv("FALKORDB_GRAPH", "delta")
    safe_login = "".join(ch for ch in login.lower() if ch.isalnum() or ch in "_-")
    graph_name = "whatif_" + safe_login + "_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f") + "_" + uuid.uuid4().hex[:12]
    copy_command = f"GRAPH.COPY {source_name} {graph_name}"
    delete_command = f"GRAPH.DELETE {graph_name}"
    cypher: list[str] = [copy_command]
    try:
        # GRAPH.COPY is a native command, and the only writes below target this disposable graph.
        # FalkorDB forks one graph copy at a time; serialize only the native copy operation.
        with _COPY_LOCK:
            client.connection.execute_command("GRAPH.COPY", source_name, graph_name)
        graph = client.select_graph(graph_name)
        deadline = time.monotonic() + 5.0
        while True:
            try:
                graph.ro_query("MATCH (n) RETURN count(n)")
                break
            except Exception as exc:
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"Copied graph {graph_name!r} did not become queryable within 5 seconds") from exc
                time.sleep(0.05)

        before_rows = _read_rows(graph, "09c_whatif_membership")
        before = {person: group for person, group in before_rows}
        before_sizes = Counter(before.values())
        direct_rows = _read_rows(graph, "09f_whatif_collaborators", {"login": login})
        direct = direct_rows[0][0] if direct_rows else []
        bridge_query = load_query("09_bridges")
        bridge_rows = graph.ro_query(bridge_query, {"limit": 1000000}).result_set
        betweenness_rank = next((rank for rank, row in enumerate(bridge_rows, 1) if row[0] == login), None)

        remove_query = load_query("09d_whatif_remove_active")
        graph.query(remove_query, {"login": login})
        after_rows = _read_rows(graph, "09c_whatif_membership")
        after = {person: group for person, group in after_rows}
        after_sizes = Counter(after.values())

        former_group = before.get(login)
        former_people = {person for person, group in before.items() if group == former_group and person != login}
        largest_after_group = max(after_sizes, key=after_sizes.get) if after_sizes else None
        cut_off = sorted(person for person in former_people if after.get(person) != largest_after_group)
        rows = [{
            "login": login,
            "mainGroupBefore": max(before_sizes.values(), default=0),
            "mainGroupAfter": max(after_sizes.values(), default=0),
            "cutOff": cut_off,
            "directCollaborators": len(direct),
            "betweennessRank": betweenness_rank,
            "nonSingletonGroupsBefore": sum(size > 1 for size in before_sizes.values()),
            "nonSingletonGroupsAfter": sum(size > 1 for size in after_sizes.values()),
        }]

        evidence_people = sorted(set(direct) | set(cut_off) | {login})
        graph_query = load_query("09e_whatif_graph")
        result = graph.ro_query(graph_query, {"people": evidence_people})
        nodes, relationships = {}, {}
        for person, rel, neighbor in result.result_set:
            for raw_node in (person, neighbor):
                node = node_dict(raw_node)
                if node:
                    nodes[node["id"]] = node
            edge = rel_dict(rel)
            if edge:
                relationships[(edge["source"], edge["target"], edge["type"])] = edge

        query_names = ["09c_whatif_membership", "09f_whatif_collaborators", "09_bridges"]
        cypher.extend(load_query(name) for name in query_names)
        cypher.extend([remove_query, load_query("09c_whatif_membership"), graph_query, delete_command])
        return {
            "tool": "simulate_departure",
            "params": {"login": login},
            "cypher": cypher,
            "rows": rows,
            "graph": {"nodes": list(nodes.values()), "edges": list(relationships.values())},
        }
    finally:
        try:
            client.connection.execute_command("GRAPH.DELETE", graph_name)
        except Exception:
            pass

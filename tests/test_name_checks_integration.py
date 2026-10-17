"""Read-only checks against the public delta snapshot; no memory or model calls."""
from time import perf_counter

import pytest
from redis.exceptions import RedisError

from busfactor.db import get_graph
from busfactor.tools import resolve_inputs, run_check_query

pytestmark = pytest.mark.integration


def test_live_name_checks_suggestions_and_timings():
    graph = get_graph("delta")
    try:
        started = perf_counter()
        active = run_check_query("17c_active_person", {"login": "harperjiang"}, graph=graph)
        check_ms = (perf_counter() - started) * 1000
    except (RedisError, OSError) as exc:
        pytest.skip(f"FalkorDB is unreachable: {exc}")
    assert active == [{"login": "harperjiang", "name": "Hao Jiang"}]
    assert run_check_query("17c_active_person", {"login": "harper-jiang"}, graph=graph) == []
    assert run_check_query("17e_person_status", {"login": "harper-jiang"}, graph=graph) == []
    for login, bot in [("tmarzec", False), ("ghost", True)]:
        assert run_check_query("17c_active_person", {"login": login}, graph=graph) == []
        person = run_check_query("17e_person_status", {"login": login}, graph=graph)[0]
        assert person["active"] is False and person["bot"] is bot
    old = resolve_inputs("departure_impact", {"login": "tmarzec"}, graph=graph)
    assert old["outcome"] == "inactive_person" and old["checks"][0]["lastSeen"] == "2025-10-14"
    assert run_check_query("17d_component_exists", {"component": "flink/inttest"}, graph=graph)
    assert run_check_query("17d_component_exists", {"component": "flink/intest"}, graph=graph) == []
    assert run_check_query("17f_component_prefix", {"prefix": "flink/"}, graph=graph)[0]["count"] > 0
    assert run_check_query("17f_component_prefix", {"prefix": "missing-area/"}, graph=graph) == [{"count": 0}]
    decision = run_check_query("17g_decision_exists", {"slug": "catalog-managed"}, graph=graph)[0]
    assert decision["status"] == "accepted"
    assert run_check_query("17g_decision_exists", {"slug": "managed-commit"}, graph=graph) == []
    assert run_check_query("17h_file_exists", {"path": "README.md"}, graph=graph) == [{"path": "README.md", "exists": True}]
    assert run_check_query("17i_module_exists", {"name": "flink"}, graph=graph) == [{"name": "flink"}]
    started = perf_counter()
    names = run_check_query("17j_reply_names", graph=graph)
    catalogue_ms = (perf_counter() - started) * 1000
    assert any(row["kind"] == "person" and row["name"] == "harperjiang" for row in names)
    assert not any(row["kind"] == "person" and row["name"] == "ghost" for row in names)
    assert all("/" in row["name"] for row in names if row["kind"] == "component")
    assert any(row["kind"] == "decision" and row["alias"] == "catalog-managed" for row in names)
    print(f"\n17c_active_person: {check_ms:.2f} ms; 17j_reply_names: {catalogue_ms:.2f} ms ({len(names)} rows)")
    for tool, params, expected in [
        ("departure_impact", {"login": "harper-jiang"}, "harperjiang"),
        ("successor", {"login": "harperjiang", "component": "flink/intest"}, "flink/inttest"),
        ("why_not", {"slug": "managed-commit"}, "managed-commits"),
    ]:
        result = resolve_inputs(tool, params, graph=graph)
        assert result["outcome"] == "unknown_entity"
        failed = next(check for check in result["checks"] if check["status"] == "not_in_graph")
        assert failed["suggestions"][0]["key"] == expected
        print(f"{failed['value']}: {failed['suggestions']}")

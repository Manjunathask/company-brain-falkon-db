"""Name resolution and outcome contracts, without a database or model provider."""
import json
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from busfactor import tools
from busfactor.agent import loop
from busfactor.agent.llm import ScriptedLLM, Step
from busfactor.agent.reply_check import check_reply
from busfactor.team_memory import TeamMemory

CATALOGUE = [
    {"kind": "person", "name": "harperjiang", "alias": "Hao Jiang"},
    {"kind": "person", "name": "tdas", "alias": "Tathagata Das"},
    {"kind": "person", "name": "abc", "alias": "Short Login"},
    {"kind": "component", "name": "flink/inttest", "alias": "flink/inttest"},
    {"kind": "decision", "name": "Catalog-Managed Tables", "alias": "catalog-managed"},
]
OLD_DATE = int(datetime(2025, 10, 14, tzinfo=timezone.utc).timestamp() * 1000)


class FakeMemory:
    def __init__(self):
        self.writes = []
        self.episodes = []

    def recall_for_prompt(self, *args, **kwargs):
        return [{"entity": "person:remembered", "corrections": [{"text": "PR #9876"}]}]

    def record_episode(self, *args):
        self.episodes.append(args)

    def store_correction(self, **params):
        self.writes.append(params)
        return {"rows": [params], "graph": {}}

    def mark_unavailable(self, **params):
        self.writes.append(params)
        return {"rows": [params], "graph": {}}


@pytest.fixture
def checks(monkeypatch):
    calls = []
    def run(name, params=None, *, graph=None):
        params = params or {}
        calls.append((name, params))
        if name == "17j_reply_names":
            return CATALOGUE
        if name == "17c_active_person":
            return [{"login": "harperjiang", "name": "Hao Jiang"}] if params["login"] == "harperjiang" else []
        if name == "17e_person_status":
            return [{"login": params["login"], "name": "Tomasz Marzec", "lastSeen": OLD_DATE,
                     "bot": params["login"] == "ghost", "active": False}] if params["login"] in {"tmarzec", "ghost"} else []
        if name == "17d_component_exists":
            return [{"component": params["component"]}] if params["component"] in {"flink/inttest", "kernel/kernel-api"} else []
        if name == "17f_component_prefix":
            return [{"count": 2 if params["prefix"] == "flink/" else 0}]
        if name == "17g_decision_exists":
            return [{"slug": "catalog-managed", "title": "Catalog-Managed Tables", "status": "accepted"}] if params["slug"] == "catalog-managed" else []
        if name == "17h_file_exists":
            return [{"path": "old/file.scala", "exists": False}] if params["path"] == "old/file.scala" else []
        if name == "17i_module_exists":
            return [{"name": "flink"}] if params["name"] == "flink" else []
        if name == "13_find_entity":
            # Matches are deliberately out of order and include the wrong kind.
            text = params["text"]
            rows = [
                {"kind": "component", "key": "connectors/examples/flink-example/a", "label": "Example"},
                {"kind": "person", "key": "leoojiang", "label": "leoojiang"},
                {"kind": "person", "key": "harperjiang", "label": "Hao Jiang"},
                {"kind": "component", "key": "flink/inttest", "label": "flink/inttest"},
            ]
            return [row for row in rows if text in row["key"] or text in row["label"]]
        raise AssertionError(name)
    monkeypatch.setattr(tools, "run_check_query", run)
    monkeypatch.setattr(tools, "find_entity", lambda text: {"graph": {}})
    monkeypatch.setattr(TeamMemory, "recall", lambda self, keys: [
        {"kind": "user_claim", "agent": "fixture", "text": "PR #5432", "entity": "person:team-person"}])
    return calls


def ask_tool(name, params, text="A checked answer.", memory=None):
    llm = ScriptedLLM([
        Step("tool_use", tool_calls=[{"id": "one", "name": name, "input": params}]),
        Step("end", text=text)])
    memory = memory or FakeMemory()
    answer = loop.ask("Check this area", "testnamechecks", llm=llm, memory=memory, graph=object())
    payload = json.loads(llm.seen_messages[1][-1]["content"][0]["content"])
    return answer, payload, memory


def test_unknown_login_blocks_main_preserves_answer_and_suggests(checks, monkeypatch):
    main = Mock(side_effect=AssertionError("must not run"))
    monkeypatch.setitem(tools.TOOLS, "departure_impact", main)
    text = "harper-jiang is not in the graph; did you mean harperjiang?"
    answer, payload, memory = ask_tool("departure_impact", {"login": "harper-jiang"}, text)
    assert payload["outcome"] == "unknown_entity"
    assert payload["rows"] == [] and payload["row_count"] == 0
    check = payload["checks"][0]
    assert check["suggestions"][0] == {"key": "harperjiang", "label": "Hao Jiang"}
    assert all(item["key"] in {"harperjiang", "leoojiang"} for item in check["suggestions"])
    assert payload["note"] == tools.UNKNOWN_NOTE
    assert answer["answer"] == text
    assert answer["entities"] == answer["followups"] == memory.writes == []
    assert answer["reply_check"]["unmatched"] == []  # suggestion was actually shown to the model
    assert "cypher" not in check["queries"][0]
    assert "MATCH" in answer["tool_calls"][0]["checks"][0]["queries"][0]["cypher"]
    main.assert_not_called()


@pytest.mark.parametrize("login,bot", [("tmarzec", False), ("ghost", True)])
def test_inactive_person_has_date_and_blocks_main(checks, monkeypatch, login, bot):
    main = Mock(side_effect=AssertionError("must not run"))
    monkeypatch.setitem(tools.TOOLS, "departure_impact", main)
    answer, payload, _ = ask_tool("departure_impact", {"login": login})
    assert payload["outcome"] == "inactive_person"
    assert payload["checks"][0]["lastSeen"] == "2025-10-14"
    assert payload["checks"][0]["bot"] is bot
    assert "2025-10-14" in payload["note"] and "last 12 months" in payload["note"]
    assert "Nothing else was run" in payload["note"]
    assert answer["answer"] == "A checked answer."
    main.assert_not_called()


def test_checks_all_arguments_and_only_component_fails(checks, monkeypatch):
    main = Mock(side_effect=AssertionError("must not run"))
    monkeypatch.setitem(tools.TOOLS, "successor", main)
    _, payload, _ = ask_tool("successor", {"login": "harperjiang", "component": "flink/intest"})
    assert payload["outcome"] == "unknown_entity"
    assert [(c["arg"], c["status"]) for c in payload["checks"]] == [("login", "ok"), ("component", "not_in_graph")]
    assert payload["checks"][1]["suggestions"][0]["key"] == "flink/inttest"
    assert ("17e_person_status", {"login": "harperjiang"}) not in checks
    assert ("13_find_entity", {"text": "flink/", "limit": 10000}) in checks
    main.assert_not_called()
    both = tools.resolve_inputs("successor", {"login": "missing", "component": "missing/area"}, graph=object())
    assert [c["status"] for c in both["checks"]] == ["not_in_graph", "not_in_graph"]


@pytest.mark.parametrize("name,params", [
    ("departure_impact", {"login": "harperjiang"}),
    ("successor", {"login": "harperjiang", "component": "kernel/kernel-api"}),
    ("orphaned_decisions", {"login": "harperjiang"}),
    ("why_not", {"slug": "catalog-managed"}),
    ("groups", {}),
])
def test_empty_rows_name_the_threshold(checks, monkeypatch, name, params):
    monkeypatch.setitem(tools.TOOLS, name, lambda **kwargs: {"rows": [], "graph": {}})
    answer, payload, _ = ask_tool(name, params)
    assert payload["outcome"] == "no_qualifying_evidence"
    assert tools.EMPTY_THRESHOLDS[name] in payload["note"]
    assert payload["note"].endswith("The graph holds no qualifying evidence for this; do not read it as nothing being at risk.")
    assert answer["answer"] == "A checked answer."


def test_empty_search_says_no_match_not_risk(checks, monkeypatch):
    monkeypatch.setitem(tools.TOOLS, "find_entity", lambda **kwargs: {"rows": [], "graph": {}})
    _, payload, _ = ask_tool("find_entity", {"text": "harper-jiang"})
    assert payload["outcome"] == "no_qualifying_evidence"
    assert payload["note"] == tools.EMPTY_NOTES["find_entity"] and "risk" not in payload["note"]


def test_rows_are_ok(checks, monkeypatch):
    monkeypatch.setitem(tools.TOOLS, "departure_impact", lambda **kwargs: {"rows": [{"component": "flink/inttest"}]})
    _, payload, _ = ask_tool("departure_impact", {"login": "harperjiang"})
    assert payload["outcome"] == "ok" and payload["row_count"] == 1
    assert payload["checks"][0]["status"] == "ok"


def test_unknown_availability_writes_nothing(checks):
    _, payload, memory = ask_tool("mark_unavailable", {"login": "missing", "reason": "away"})
    assert payload["outcome"] == "unknown_entity" and memory.writes == []


@pytest.mark.parametrize("key", ["person:tmarzec", "component:flink/inttest", "module:flink", "decision:catalog-managed"])
def test_correction_allows_existing_inactive_people_and_other_keys(checks, key):
    _, payload, memory = ask_tool("remember_correction", {"key": key, "text": "A user correction"})
    assert payload["outcome"] == "ok" and len(memory.writes) == 1
    if key.startswith("person:"):
        assert not any(name == "17c_active_person" for name, _ in checks)


@pytest.mark.parametrize("key", ["person:missing", "component:missing", "module:missing", "decision:missing"])
def test_unknown_correction_key_writes_nothing(checks, key):
    _, payload, memory = ask_tool("remember_correction", {"key": key, "text": "A user correction"})
    assert payload["outcome"] == "unknown_entity" and memory.writes == []


def test_prefix_and_historical_file_checks(checks):
    good = tools.resolve_inputs("departure_files", {"login": "harperjiang", "componentPrefix": "flink/"}, graph=object())
    assert good["outcome"] == "ok"
    bad = tools.resolve_inputs("departure_files", {"login": "harperjiang", "componentPrefix": "missing/"}, graph=object())
    assert bad["outcome"] == "unknown_entity"
    checks.clear()
    tools.resolve_inputs("departure_impact", {"login": "harperjiang", "componentPrefix": ""}, graph=object())
    assert not any(name == "17f_component_prefix" for name, _ in checks)
    assert tools.resolve_inputs("decision_trace", {"path": "old/file.scala"}, graph=object())["outcome"] == "ok"
    assert tools.resolve_inputs("decision_trace", {"path": "missing/file.scala"}, graph=object())["outcome"] == "unknown_entity"


@pytest.mark.parametrize("candidates,reading,expected", [([], [], "no_qualifying_evidence"), ([{}], [], "ok"), ([], [{}], "ok")])
def test_handover_packet_empty_means_no_candidates_and_no_reading(checks, monkeypatch, candidates, reading, expected):
    monkeypatch.setattr(loop.handover, "plan_tool", lambda **kwargs: {"rows": [{"candidates": candidates, "read": reading}]})
    _, payload, _ = ask_tool("handover_plan", {"login": "harperjiang", "component": "flink/inttest"})
    assert payload["outcome"] == expected


def test_api_returns_same_blocked_metadata_with_200(checks, monkeypatch):
    import busfactor.api.app as api
    main = Mock(side_effect=AssertionError("must not run"))
    monkeypatch.setitem(tools.TOOLS, "departure_impact", main)
    response = TestClient(api.app).post("/api/tools/departure_impact", json={"params": {"login": "harper-jiang"}})
    assert response.status_code == 200
    result = response.json()
    assert result["outcome"] == "unknown_entity" and result["rows"] == []
    assert result["note"] == tools.UNKNOWN_NOTE and result["checks"][0]["suggestions"][0]["key"] == "harperjiang"
    main.assert_not_called()


def test_cli_uses_resolver(checks, monkeypatch, capsys):
    import sys
    main = Mock(side_effect=AssertionError("must not run"))
    # Keep the function signature for CLI argument filtering.
    def departure(login):
        return main(login)
    monkeypatch.setitem(tools.TOOLS, "departure_impact", departure)
    monkeypatch.setattr(sys, "argv", ["tools", "departure_impact", "--login", "harper-jiang"])
    tools.main()
    assert "unknown_entity" in capsys.readouterr().out
    main.assert_not_called()


def test_reply_names_all_in_rows():
    rows = [{"pr": 4381, "login": "harperjiang", "component": "flink/inttest", "slug": "catalog-managed"}]
    result = check_reply("PR #4381: @harperjiang in `flink/inttest` discussed Catalog-Managed Tables", json.dumps(rows), CATALOGUE)
    assert result == {"checked": 4, "unmatched": []}


def test_reply_reports_exactly_three_unmatched():
    result = check_reply("#6189, tdas and `flink/intest`", "[]", CATALOGUE)
    assert result == {"checked": 3, "unmatched": [
        {"kind": "pr", "text": "#6189"}, {"kind": "person", "text": "tdas"}, {"kind": "path", "text": "flink/intest"}]}


def test_reply_ignores_ordinary_words_short_logins_and_partial_tokens():
    result = check_reply("#1 candidate abc ordinary words x-tdas x_tdas x/tdas x.tdas `https://example.com/a`", "", CATALOGUE)
    assert result == {"checked": 0, "unmatched": []}
    assert check_reply("tdas", "x-tdas x_tdas x/tdas x.tdas", CATALOGUE)["unmatched"]


@pytest.mark.parametrize("text", ["#4381", "PR 4381", "PR #4381", "issue #4381", "https://github.com/delta-io/delta/pull/4381", "https://github.com/delta-io/delta/issues/4381"])
def test_reply_number_formats_and_whole_number(text):
    assert check_reply(text, "4381", []) == {"checked": 1, "unmatched": []}
    assert check_reply(text, "14381", [])["unmatched"] == [{"kind": "pr", "text": "#4381"}]


def test_reply_case_insensitive_distinct_mentions_and_question_names():
    assert check_reply("TDAS and @tdas and PR 4381 and #4381", "Question: tdas and #4381?", CATALOGUE) == {"checked": 2, "unmatched": []}
    assert check_reply("@new-person", "question: new-person", []) == {"checked": 1, "unmatched": []}


def test_reply_sees_memory_team_memory_and_tool_results(checks, monkeypatch):
    monkeypatch.setitem(tools.TOOLS, "groups", lambda: {"rows": [{"pr": 1234}]})
    answer, _, _ = ask_tool("groups", {}, "#9876, #5432 and #1234")
    assert answer["reply_check"] == {"checked": 3, "unmatched": []}


def test_reply_catalogue_failure_still_checks_patterns(checks, monkeypatch):
    original = tools.run_check_query
    def query(name, params=None, *, graph=None):
        if name == "17j_reply_names":
            raise RuntimeError("fake graph catalogue missing")
        return original(name, params, graph=graph)
    monkeypatch.setattr(tools, "run_check_query", query)
    monkeypatch.setitem(tools.TOOLS, "groups", lambda: {"rows": [{"groups": 3}]})
    warning = Mock()
    monkeypatch.setattr(loop.LOGGER, "warning", warning)
    answer, _, _ = ask_tool("groups", {}, "#6189 is here")
    assert answer["answer"] == "#6189 is here"
    assert answer["reply_check"] == {"checked": 1, "unmatched": [{"kind": "pr", "text": "#6189"}]}
    assert warning.call_count == 2
    assert "catalogue unavailable" in warning.call_args_list[0].args[0]
    assert warning.call_args_list[1].args[0] == "reply_check visitor=%s unmatched=%s"


def test_failed_tool_stays_error_and_fixed_fallback_skips_reply_check(checks, monkeypatch):
    monkeypatch.setitem(tools.TOOLS, "groups", Mock(side_effect=RuntimeError("unavailable")))
    llm = ScriptedLLM([Step("tool_use", tool_calls=[{"id": "x", "name": "groups", "input": {}}]), Step("end", text="#6189")])
    result = loop.ask("question", "testnamechecks", llm=llm, graph=object(), memory=FakeMemory())
    assert llm.seen_messages[1][-1]["content"][0]["is_error"]
    assert result["tool_calls"][0]["outcome"] == "error"
    assert result["answer"].startswith("I could not establish")
    assert not any(name == "17j_reply_names" for name, _ in checks)

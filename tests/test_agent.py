import json

from busfactor.agent.llm import ScriptedLLM, Step
from busfactor.agent.loop import ask, _first_user_message
from busfactor.agent.memory import entity_keys


class FakeMemory:
    def __init__(self): self.saved = []
    def recall(self, **kwargs): return [{"entity":"person:alice", "corrections":[{"text":"fixture correction"}]}]
    def record_episode(self, *args): self.saved.append(args)


def _result(tool, params, nodes=(), edges=(), rows=()):
    return {"tool":tool, "params":params, "cypher":"MATCH (n) RETURN n", "rows":list(rows),
            "graph":{"nodes":list(nodes), "edges":list(edges)}}


def test_loop_parallel_calls_are_returned_in_one_tool_message_and_deduplicate(monkeypatch):
    from busfactor.agent import loop
    node = {"id":1,"label":"Person","key":"huan233usc","props":{}}
    edge = {"source":1,"target":2,"type":"KNOWS","props":{}}
    monkeypatch.setitem(loop.graph_tools.TOOLS, "departure_impact", lambda **p: _result("departure_impact",p,[node],[edge],[{"component":"kernel"}]))
    monkeypatch.setitem(loop.graph_tools.TOOLS, "departure_files", lambda **p: _result("departure_files",p,[node],[edge],[{"component":"kernel"}]))
    llm = ScriptedLLM([
        Step("tool_use", tool_calls=[{"id":"a","name":"departure_impact","input":{"login":"huan233usc"}},
                                     {"id":"b","name":"departure_files","input":{"login":"huan233usc"}}]),
        Step("end", text="The graph reports the requested results.")])
    memory = FakeMemory()
    answer = ask("what if huan233usc leaves", "testuser", llm=llm, memory=memory, graph=object())
    assert answer["answer"] == "The graph reports the requested results."
    assert len(answer["tool_calls"]) == 2
    second_call_history = llm.seen_messages[1]
    tool_messages = [m for m in second_call_history if m["role"] == "user" and isinstance(m["content"], list)]
    assert len(tool_messages) == 1 and len(tool_messages[0]["content"]) == 2
    assert len(answer["graph"]["nodes"]) == 1 and len(answer["graph"]["edges"]) == 1
    assert answer["entities"] == ["person:huan233usc"]
    assert len(memory.saved) == 1
    first_user = llm.seen_messages[0][0]["content"]
    assert "What you remember about this user:" in first_user
    assert "fixture correction" in first_user
    assert "Today is " in first_user and "Question: what if huan233usc leaves" in first_user


def test_tool_result_is_capped_and_excludes_evidence_graph(monkeypatch):
    from busfactor.agent import loop
    rows = [{"index":i,"paths":[f"path-{i}-{n}" for n in range(12)]} for i in range(50)]
    graph = {"nodes":[{"id":i,"label":"File","key":f"file-{i}"} for i in range(200)],"edges":[]}
    monkeypatch.setitem(loop.graph_tools.TOOLS, "groups", lambda: {"tool":"groups", "params":{},
        "cypher":"MATCH (n) RETURN n", "rows":rows, "graph":graph})
    llm = ScriptedLLM([Step("tool_use",tool_calls=[{"id":"groups-1","name":"groups","input":{}}]),
                       Step("end",text="A graph result was returned.")])
    answer = ask("summarize", "testuser", llm=llm, memory=FakeMemory(), graph=object())
    result_message = llm.seen_messages[1][-1]
    payload = json.loads(result_message["content"][0]["content"])
    assert set(payload) == {"tool", "row_count", "rows", "truncated"}
    assert payload["row_count"] == 50 and payload["truncated"] == 10
    assert len(payload["rows"]) == 40
    assert payload["rows"][0]["paths"] == {"items":[f"path-0-{n}" for n in range(10)],"truncated":2}
    assert "graph" not in payload and len(answer["graph"]["nodes"]) == 200
    assert answer["tool_calls"][0]["tool_result_chars"] == len(json.dumps(result_message["content"][0], ensure_ascii=False))


def test_first_user_message_is_readable_and_omits_empty_memory():
    message = _first_user_message("how many modules?", "2026-10-16", [])
    assert message == "Today is 2026-10-16.\n\nQuestion: how many modules?"
    recalled = _first_user_message("question", "2026-10-16", [{"entity":"module:kernel"}])
    assert "What you remember about this user:" in recalled
    assert '"module:kernel"' in recalled


def test_bad_tool_input_is_error_and_does_not_make_graph_claims():
    llm = ScriptedLLM([Step("tool_use",tool_calls=[{"id":"x","name":"departure_impact","input":{"login":5}}]),
                       Step("end",text="I cannot support a graph conclusion.")])
    answer = ask("question", "testuser", llm=llm, memory=FakeMemory(), graph=object())
    result_message = llm.seen_messages[1][-1]
    assert result_message["content"][0]["is_error"] is True
    assert "login must be string" in result_message["content"][0]["content"]
    assert answer["answer"].startswith("I could not establish")


def test_tool_round_limit_requests_one_final_answer(monkeypatch):
    from busfactor.agent import loop
    monkeypatch.setitem(loop.graph_tools.TOOLS, "groups", lambda: _result("groups",{},rows=[{"groups":1}]))
    steps = [Step("tool_use",tool_calls=[{"id":str(i),"name":"groups","input":{}}]) for i in range(8)]
    steps.append(Step("end",text="Eight rounds completed with graph evidence."))
    llm = ScriptedLLM(steps)
    result = ask("question", "testuser", llm=llm, memory=FakeMemory(), graph=object())
    assert len(result["tool_calls"]) == 8
    assert result["stop_reason"] == "round_limit"
    assert result["answer"] == "Eight rounds completed with graph evidence."
    assert len(llm.steps) == 0


def test_memory_entity_keys_only_include_supported_types():
    assert entity_keys({"nodes":[{"label":"Person","key":"alice"},{"label":"File","key":"x.py"},
                         {"label":"Component","key":"kernel"},{"label":"Decision","key":"rfc"}]}) == [
                             "component:kernel", "decision:rfc", "person:alice"]

from busfactor import bootstrap


class FakeClient:
    def __init__(self, graphs):
        self.graphs = graphs
        self.connection = self

    def list_graphs(self):
        return list(self.graphs)

    def ping(self):
        return True


class FakeResult:
    def __init__(self, nodes, relationships):
        self.result_set = [[nodes, relationships]]


class FakeGraph:
    def __init__(self, graphs=(), nodes=0, relationships=0):
        self.client = FakeClient(set(graphs))
        self.nodes = nodes
        self.relationships = relationships
        self.count_reads = 0

    def ro_query(self, query, params):
        self.count_reads += 1
        return FakeResult(self.nodes, self.relationships)


def test_missing_graph_runs_snapshot_bootstrap(monkeypatch):
    graph = FakeGraph()
    calls = []

    def run(command, *, check, env):
        calls.append((command, env))
        if "busfactor.load" in command:
            graph.client.graphs.add("delta")
            graph.nodes = 7
        elif "busfactor.link_decisions" in command:
            graph.relationships = 3

    monkeypatch.setattr(bootstrap.sys, "executable", "python")
    loaded = bootstrap.bootstrap_graph(graph, "delta", env={}, run=run)

    assert loaded is True
    assert len(calls) == 3
    assert "busfactor.load" in calls[0][0]
    assert "--from-snapshot" in calls[0][0]
    assert all(call_env["BUSFACTOR_INPUT"] == "snapshot" for _, call_env in calls)
    assert graph.count_reads == 3


def test_existing_nonempty_graph_skips_snapshot_bootstrap():
    graph = FakeGraph(graphs={"delta"}, nodes=12, relationships=20)
    calls = []

    loaded = bootstrap.bootstrap_graph(graph, "delta", run=lambda *a, **k: calls.append(a))

    assert loaded is False
    assert calls == []
    assert graph.count_reads == 2

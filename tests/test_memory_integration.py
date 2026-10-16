"""Memory and changed-since Cypher tests on isolated throwaway graphs."""
import os

import pytest
from falkordb import FalkorDB
from redis.exceptions import RedisError, ResponseError

from busfactor.agent.memory import Memory
from busfactor.db import load_query

pytestmark = pytest.mark.integration
MEMORY_GRAPH = "mem_test_wp7"
FIXTURE_GRAPH = "bf_test"


def _delete(client, name):
    try: client.connection.execute_command("GRAPH.DELETE", name)
    except ResponseError: pass


@pytest.fixture
def graphs():
    try:
        client = FalkorDB(host=os.getenv("FALKORDB_HOST","localhost"),port=int(os.getenv("FALKORDB_PORT","6379")),password=os.getenv("FALKORDB_PASSWORD") or None)
        client.connection.ping()
    except (RedisError,OSError,ConnectionError) as exc:
        pytest.skip(f"FalkorDB is unreachable: {exc}")
    _delete(client,MEMORY_GRAPH); _delete(client,FIXTURE_GRAPH)
    memory = client.select_graph(MEMORY_GRAPH)
    delta_fixture = client.select_graph(FIXTURE_GRAPH)
    yield client,memory,delta_fixture
    _delete(client,MEMORY_GRAPH); _delete(client,FIXTURE_GRAPH); client.close()


def test_memory_record_recall_correction_and_changed_since(graphs):
    _client, memory_graph, delta = graphs
    delta.query("""
      CREATE (p:Person {login:'alice'})-[:AUTHORED]->(c:Commit {sha:'newer',ts:200,subject:'new'})
      CREATE (c)-[:PART_OF]->(pr:PR {number:42,title:'Fixture PR',mergedAt:200})
      CREATE (p)-[:KNOWS]->(component:Component {name:'kernel/test'})
      CREATE (:Module {name:'kernel'})
      CREATE (:Decision {slug:'fixture-decision'})
    """)
    memory = Memory("test_wp7", graph=memory_graph)
    memory.record_episode("session-1", "what changed?", "A fixture answer", ["find_entity"], ["person:alice"], ts=100)
    memory.store_correction("person:alice", "Alice still owns kernel", "user", ts=110)
    recalled = memory.recall(delta_graph=delta)
    assert recalled[0]["entity"] == "person:alice"
    assert recalled[0]["earlierQuestions"] == ["what changed?"]
    assert recalled[0]["corrections"][0]["text"] == "Alice still owns kernel"
    changes = recalled[0]["changedSinceLastAsked"][0]
    assert changes["commitCount"] == 1
    assert changes["prCount"] == 1
    assert changes["prs"][0]["number"] == 42
    assert changes["commits"][0]["sha"] == "newer"


def test_changed_since_fixture_components_modules_and_decisions(graphs):
    _client, _memory_graph, delta = graphs
    delta.query("""
      CREATE (m:Module {name:'kernel'})<-[:IN_MODULE]-(f:File {path:'kernel/A.scala'})
      CREATE (component:Component {name:'kernel/test'})<-[:IN_COMPONENT]-(f)
      CREATE (c:Commit {sha:'change',ts:500,subject:'change'})-[:TOUCHED]->(f)
      CREATE (p:PR {number:9,title:'Fixture',mergedAt:550})-[:IMPLEMENTS]->(d:Decision {slug:'fixture'})
    """)
    query = load_query("14d_changed_since")
    for kind, key in [("component","kernel/test"),("module","kernel"),("decision","fixture")]:
        result = delta.ro_query(query,{"kind":kind,"key":key,"since":100})
        assert result.result_set
        counts = dict(zip([h[1] for h in result.header], result.result_set[0]))
        if kind in {"component", "module"}:
            assert counts["commitCount"] == 1
            assert counts["commits"][0]["sha"] == "change"
        if kind == "decision":
            assert counts["prCount"] == 1
            assert counts["prs"][0]["number"] == 9


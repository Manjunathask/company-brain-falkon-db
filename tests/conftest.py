"""Shared isolated FalkorDB graph for API integration tests."""
import os

import pytest
from falkordb import FalkorDB
from redis.exceptions import RedisError, ResponseError


@pytest.fixture
def graph():
    graph_name = "bf_api_test"
    try:
        client = FalkorDB(host=os.getenv("FALKORDB_HOST", "localhost"),
                          port=int(os.getenv("FALKORDB_PORT", "6379")),
                          password=os.getenv("FALKORDB_PASSWORD") or None)
        client.connection.ping()
    except (RedisError, OSError, ConnectionError) as exc:
        pytest.skip(f"FalkorDB is unreachable: {exc}")
    try:
        try:
            client.connection.execute_command("GRAPH.DELETE", graph_name)
        except ResponseError:
            pass
        g = client.select_graph(graph_name)
        g.query("""
            CREATE (alice:Person:Active {login:'alice',name:'Alice',bot:false,lastSeen:1800000000000}),
                   (bob:Person:Active {login:'bob',name:'Bob',bot:false,lastSeen:1800000000000}),
                   (carol:Person:Active {login:'carol',name:'Carol',bot:false,lastSeen:1800000000000}),
                   (m:Module {name:'spark'}), (comp:Component {name:'spark/test'})-[:IN_MODULE]->(m),
                   (f:File {path:'spark/test/A.scala'})-[:IN_COMPONENT]->(comp),
                   (f)-[:IN_MODULE]->(m),
                   (d:Decision {slug:'fixture-rfc',title:'Fixture RFC',status:'accepted'}),
                   (issue:Issue {number:501,title:'Fixture RFC issue'}),
                   (d)-[:TRACKED_IN]->(issue),
                   (pr:PR {number:501,title:'Fixture RFC PR'})-[:IMPLEMENTS {confidence:'high',via:'issue-ref'}]->(d),
                   (alice)-[:OPENED]->(pr),
                   (alice)-[:PARTICIPATED_IN {confidence:'high'}]->(d),
                   (alice)-[:WORKS_WITH]->(bob), (bob)-[:WORKS_WITH]->(carol)
            WITH alice,bob,carol,f,comp,m
            UNWIND [{p:alice,sha:'a1'},{p:bob,sha:'b1'},{p:carol,sha:'c1'}] AS row
            WITH row.p AS person,row.sha AS sha,f,alice,bob,carol,comp,m
            CREATE (person)-[:AUTHORED]->(c:Commit {sha:sha,ts:1800000000000,subject:'fixture'})
            CREATE (c)-[:TOUCHED]->(f)
            WITH alice,bob,carol,comp,m
            CREATE (alice)-[a:KNOWS]->(comp) SET a.commits=3,a.lastTouched=1800000000000
            CREATE (bob)-[b:KNOWS]->(comp) SET b.commits=2,b.lastTouched=1800000000000
            CREATE (alice)-[am:KNOWS]->(m) SET am.commits=3,am.lastTouched=1800000000000
            CREATE (bob)-[bm:KNOWS]->(m) SET bm.commits=2,bm.lastTouched=1800000000000
        """)
        yield g
    finally:
        try:
            client.connection.execute_command("GRAPH.DELETE", graph_name)
        except ResponseError:
            pass
        client.close()

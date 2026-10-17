"""Integration coverage for the WP6 graph-tool registry."""
import os
from concurrent.futures import ThreadPoolExecutor
import pytest
from falkordb import FalkorDB
from redis.exceptions import RedisError, ResponseError

import busfactor.tools as tools
from busfactor.db import load_query

pytestmark = pytest.mark.integration
GRAPH_NAME = "bf_test"
NOW = 1_800_000_000_000


def _delete(client):
    try: client.connection.execute_command("GRAPH.DELETE", GRAPH_NAME)
    except ResponseError: pass

@pytest.fixture
def graph(monkeypatch):
    try:
        client = FalkorDB(host=os.getenv("FALKORDB_HOST", "127.0.0.1"), port=int(os.getenv("FALKORDB_PORT", "6379")), password=os.getenv("FALKORDB_PASSWORD") or None)
        client.connection.ping()
    except (RedisError, OSError, ConnectionError) as exc:
        pytest.skip(f"FalkorDB is unreachable: {exc}")
    _delete(client)
    g = client.select_graph(GRAPH_NAME)
    g.query("""
        CREATE (alice:Person:Active {login:'alice', name:'Alice', bot:false, lastSeen:1800000000000}),
               (bob:Person:Active {login:'bob', name:'Bob', bot:false, lastSeen:1800000000000}),
               (carol:Person:Active {login:'carol', name:'Carol', bot:false, lastSeen:1800000000000}),
               (dana:Person:Active {login:'dana', name:'Dana', bot:false, lastSeen:1800000000000}),
               (erin:Person:Active {login:'erin', name:'Erin', bot:false, lastSeen:1800000000000}),
               (bot:Person {login:'testbot[bot]',bot:true}),
               (m:Module {name:'spark'}), (comp:Component {name:'spark/test'})-[:IN_MODULE]->(m),
               (f:File {path:'spark/test/A.scala'})-[:IN_COMPONENT]->(comp),
               (f)-[:IN_MODULE]->(m),
               (f2:File {path:'icebergcompat/test/B.scala'})-[:IN_COMPONENT]->(comp),
               (f2)-[:IN_MODULE]->(m),
               (d:Decision {slug:'old-choice',title:'Old Choice',status:'rejected',decidedOn:1799000000000}),
               (new:Decision {slug:'new-choice',title:'New Choice',status:'accepted',decidedOn:1799500000000}),
               (threshold:Decision {slug:'threshold-check',title:'Threshold Check',status:'proposed',decidedOn:1799500000000}),
               (issue:Issue {number:501,title:'RFC discussion'}),
               (d)-[:SUPERSEDED_BY {source:'PR #4382'}]->(new),
               (new)-[:TRACKED_IN]->(issue),
               (d)-[:TRACKED_IN]->(issue),
               (alice)-[:PARTICIPATED_IN {confidence:'high',via:'issue'}]->(d),
               (alice)-[:PARTICIPATED_IN {confidence:'high',via:'issue'}]->(new),
               (bob)-[:PARTICIPATED_IN {confidence:'low',via:'pr'}]->(new),
               (alice)-[:PARTICIPATED_IN {confidence:'high',via:'issue'}]->(threshold),
               (bob)-[:PARTICIPATED_IN {confidence:'low',via:'pr'}]->(threshold),
               (owner:Person {login:'owner',bot:false})-[:DECLARED_OWNER {pattern:'/spark/'}]->(m),
               (pr:PR {number:501,title:'Test RFC PR',body:'RFC implementation'})-[:IMPLEMENTS {confidence:'high',via:'issue-ref'}]->(new),
               (pr)-[:REFERENCES]->(issue)
        MERGE (alice)-[:WORKS_WITH]->(bob)
        MERGE (bob)-[:WORKS_WITH]->(carol)
        MERGE (dana)-[:WORKS_WITH]->(erin)
        WITH alice,bob,carol,dana,erin,comp,m,f,f2,pr
        UNWIND [{p:alice,sha:'a1',file:f},{p:bob,sha:'b1',file:f},{p:carol,sha:'c1',file:f2},{p:alice,sha:'a2',file:f2}] AS row
        WITH row.p AS person,row.sha AS sha,row.file AS file,alice,bob,carol,dana,erin,comp,m,f,f2,pr
        CREATE (person)-[:AUTHORED]->(c:Commit {sha:sha,ts:1800000000000,subject:'fixture'})
        CREATE (c)-[:TOUCHED]->(file)
        WITH alice,bob,carol,dana,erin,comp,m
        UNWIND [{p:alice,n:3},{p:bob,n:2},{p:carol,n:1}] AS row
        WITH row.p AS person,row.n AS n,alice,bob,carol,dana,erin,comp,m
        CREATE (person)-[k:KNOWS]->(comp) SET k.commits=n,k.lastTouched=1800000000000
        CREATE (alice)-[ka:KNOWS]->(m) SET ka.commits=3,ka.lastTouched=1800000000000
        CREATE (bob)-[kb:KNOWS]->(m) SET kb.commits=2,kb.lastTouched=1800000000000
        CREATE (carol)-[kc:KNOWS]->(m) SET kc.commits=1,kc.lastTouched=1800000000000
        CREATE (alice)-[:OPENED]->(pr)
        """)
    monkeypatch.setattr(tools, "get_graph", lambda: g)
    monkeypatch.setenv("FALKORDB_GRAPH", GRAPH_NAME)
    yield g
    _delete(client)
    client.close()


def test_every_registry_tool_runs_on_fixture(graph):
    before = _snapshot(graph)
    checks = [
        tools.bus_factor(since=0,minCommits=1,minTotal=1),
        tools.bus_factor_component(since=0,minCommits=1,minTotal=1),
        tools.departure_impact('alice',since=0,minCommits=1),
        tools.departure_files('alice',since=0),
        tools.orphaned_decisions('alice'),
        tools.decision_share('alice'),
        tools.successor('alice','spark/test',since=0),
        tools.bridges(), tools.groups(), tools.simulate_departure('bob'),
        tools.decision_trace('icebergcompat/test/B.scala'),
        tools.why_not('old-choice'), tools.drift(),
        tools.declared_vs_actual(since=0,minCommits=1),
        tools.find_entity('catalog'),
    ]
    for result in checks:
        assert set(result) == {'tool','params','cypher','rows','graph'}
        assert isinstance(result['rows'],list)
        assert set(result['graph']) == {'nodes','edges'}
    assert any(row['component']=='spark/test' for row in checks[2]['rows'])
    assert next(result for result in checks if result['tool']=='why_not')['rows'][0]['chosenInstead']=='New Choice'
    group_row = next(result for result in checks if result['tool'] == 'groups')['rows'][0]
    assert group_row['groups'] == 2
    assert group_row['largestGroup'] == 3
    assert group_row['nonSingletonGroups'] == 2
    high = tools.orphaned_decisions('alice', minConfidence='high')
    low = tools.orphaned_decisions('alice', minConfidence='low')
    assert any(row['decision']=='Threshold Check' for row in high['rows'])
    assert not any(row['decision']=='Threshold Check' for row in low['rows'])
    assert _snapshot(graph) == before


def test_decision_share_counts_pr_ownership_and_lists_active_openers(graph):
    graph.query("""
        CREATE (d:Decision {slug:'share-fixture',title:'Share Fixture',status:'accepted'}),
               (p1:PR {number:901})-[:IMPLEMENTS {confidence:'high'}]->(d),
               (p2:PR {number:902})-[:IMPLEMENTS {confidence:'high'}]->(d),
               (p3:PR {number:903})-[:IMPLEMENTS {confidence:'high'}]->(d)
        WITH d,p1,p2,p3
        MATCH (alice:Person {login:'alice'}), (bob:Person {login:'bob'})
        CREATE (alice)-[:OPENED]->(p1), (alice)-[:OPENED]->(p2), (bob)-[:OPENED]->(p3)
    """)
    result = tools.decision_share('alice', minShare=0.3, minConfidence='high')
    row = next(item for item in result['rows'] if item['decision'] == 'Share Fixture')
    assert row['theirPRs'] == 2
    assert row['totalPRs'] == 3
    assert row['share'] == pytest.approx(2 / 3)
    assert row['otherOpeners'] == [{'login': 'bob', 'prs': 1}]
    assert len(result['graph']['edges']) >= 3


def test_simulate_departure_splits_group_and_cleans_copy(graph):
    client = FalkorDB(host=os.getenv("FALKORDB_HOST", "127.0.0.1"), port=int(os.getenv("FALKORDB_PORT", "6379")), password=os.getenv("FALKORDB_PASSWORD") or None)
    delta = client.select_graph('delta')
    try:
        delta_before = delta.ro_query("MATCH (n) RETURN count(n)").result_set[0][0]
    except ResponseError:
        delta_before = None
    names_before = set(client.connection.execute_command('GRAPH.LIST'))
    fixture_before = _snapshot(graph)
    result = tools.simulate_departure('bob')
    assert result['rows'][0]['mainGroupBefore']==3
    assert result['rows'][0]['mainGroupAfter']==2
    assert result['rows'][0]['cutOff']==['alice','carol']
    assert result['rows'][0]['directCollaborators']==2
    assert result['rows'][0]['nonSingletonGroupsBefore']==2
    assert result['rows'][0]['nonSingletonGroupsAfter']==1
    assert result['rows'][0]['betweennessRank'] is not None
    assert _snapshot(graph) == fixture_before
    assert set(client.connection.execute_command('GRAPH.LIST')) == names_before
    if delta_before is not None:
        assert delta.ro_query("MATCH (n) RETURN count(n)").result_set[0][0] == delta_before
    client.close()


def test_two_simulations_can_copy_same_graph_concurrently_and_clean_up(graph):
    from busfactor.db import get_client

    client = get_client()
    names_before = set(client.connection.execute_command("GRAPH.LIST"))
    fixture_before = _snapshot(graph)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(tools.simulate_departure, "alice") for _ in range(2)]
        results = [future.result(timeout=20) for future in futures]
    assert [result["rows"][0]["login"] for result in results] == ["alice", "alice"]
    assert all(result["graph"]["nodes"] for result in results)
    assert set(client.connection.execute_command("GRAPH.LIST")) == names_before
    assert _snapshot(graph) == fixture_before


def test_departure_scope_filters_and_component_prefix(graph):
    graph.query("""
        MATCH (alice:Person {login:'alice'}), (comp:Component {name:'spark/test'})
        CREATE (fixture:Component {name:'spark/test/(test-resources)'})
        CREATE (alice)-[:AUTHORED]->(c:Commit {sha:'fixture-only',ts:1800000000000})
        CREATE (c)-[:TOUCHED]->(:File {path:'fixture-only',exists:true})-[:IN_COMPONENT]->(fixture)
        CREATE (alice)-[k:KNOWS]->(fixture) SET k.commits=4,k.lastTouched=1800000000000
    """)
    default = tools.departure_impact("alice", since=0, minCommits=1)
    scoped = tools.departure_impact("alice", since=0, minCommits=1, componentPrefix="spark/test")
    included = tools.departure_impact("alice", since=0, minCommits=1, includeTestResources=True)
    assert "spark/test/(test-resources)" not in [row["component"] for row in default["rows"]]
    assert {row["component"] for row in scoped["rows"]} == {"spark/test"}
    assert "spark/test/(test-resources)" in [row["component"] for row in included["rows"]]


def test_find_entity_matches_partial_login_and_ranks_exact_first(graph):
    graph.query("CREATE (:Person {login:'alice2',name:'Alice Two',bot:false})")
    results = tools.find_entity("alice")['rows']
    people = [row for row in results if row["kind"] == "person"]
    assert people[0]["key"] == "alice"
    assert next(row for row in people if row["key"] == "alice")["score"] == 2.0
    assert next(row for row in people if row["key"] == "alice2")["score"] == 1.5


def _snapshot(graph):
    labels = graph.ro_query("MATCH (n) UNWIND labels(n) AS label RETURN label,count(*) ORDER BY label").result_set
    relationships = graph.ro_query("MATCH ()-[r]->() RETURN type(r),count(*) ORDER BY type(r)").result_set
    return labels, relationships

@pytest.fixture
def window_graph(graph):
    """Intentionally misleading KNOWS counts; only commit paths may drive recent risk."""
    day = 86_400_000
    since = NOW - 365 * day
    graph.query("""
        CREATE (m:Module {name:'window'}), (area:Component {name:'window/core'}),
               (f:File {path:'window/current',exists:true})-[:IN_COMPONENT]->(area),
               (f)-[:IN_MODULE]->(m),
               (f2:File {path:'window/current2',exists:true})-[:IN_COMPONENT]->(area),
               (f2)-[:IN_MODULE]->(m),
               (deleted:File {path:'window/deleted',exists:false})-[:IN_COMPONENT]->(area),
               (deleted)-[:IN_MODULE]->(m)
        WITH m,area
        UNWIND ['leaving','oldauthor','peer','robot'] AS login
        CREATE (p:Person:Active {login:login,bot:login='robot'})
        CREATE (p)-[:KNOWS {commits:100,lastTouched:$now}]->(area)
        CREATE (p)-[:KNOWS {commits:100,lastTouched:$now}]->(m)
    """, {'now': NOW})
    commits = []
    for login, count in [('leaving', 3), ('peer', 2), ('oldauthor', 1), ('robot', 10)]:
        for i in range(count):
            commits.append({'login': login, 'sha': f'{login}-{i}', 'ts': NOW-day*30,
                            'bulk': False, 'deleted': False})
    commits += [{'login':'oldauthor','sha':f'old-{i}','ts':NOW-day*600,
                 'bulk':False,'deleted':False} for i in range(10)]
    commits += [dict(login='oldauthor',sha=sha,ts=ts,bulk=bulk,deleted=deleted)
                for sha,ts,bulk,deleted in [('boundary',since,False,False),
                                           ('bulk',NOW,True,False),('deleted',NOW,False,True)]]
    graph.query("""
        UNWIND $rows AS row
        MATCH (p:Person {login:row.login})
        CREATE (p)-[:AUTHORED]->(c:Commit {sha:row.sha,ts:row.ts,bulk:row.bulk})
        WITH c,row
        MATCH (f:File) WHERE f.path IN CASE WHEN row.deleted THEN ['window/deleted']
                                                   ELSE ['window/current','window/current2'] END
        CREATE (c)-[:TOUCHED]->(f)
    """, {'rows':commits})
    return graph, since


def test_windowed_counts_thresholds_and_exact_author_graphs(window_graph):
    graph, since = window_graph
    params = {**tools.DEFAULTS, 'since': since, 'minTotal': 5}
    for name, column in [('05_bus_factor','module'), ('05b_bus_factor_component','component')]:
        result = tools._run(name, params, graph=graph)
        row = next(row for row in result['rows'] if row[column].startswith('window'))
        assert row['total'] == 5 and row['people'] == 2
        assert row['countedExperts'] == ['leaving'] and row['busFactor'] == 1
        area_nodes = {n['id'] for n in result['graph']['nodes'] if n['key'] == row[column]}
        nodes = {n['id']:n for n in result['graph']['nodes']}
        assert {nodes[e['source']]['key'] for e in result['graph']['edges']
                if e['target'] in area_nodes} == {'leaving'}
    assert tools.departure_impact('oldauthor', since=since)['rows'] == []
    one = tools.departure_impact('oldauthor', since=since, minCommits=1)['rows'][0]
    assert one['theirCommits'] == 1  # ten old commits do not count
    result = tools.departure_impact('leaving', since=since)
    row = result['rows'][0]
    assert row['theirCommits'] == 3
    assert row['remaining'] == ['peer'] and row['risk'] == 'ONE OTHER AUTHOR'
    assert row['reviewers'] == [] and row['reviewerCount'] == 0
    nodes = {n['id']:n for n in result['graph']['nodes']}
    assert {nodes[e['source']]['key'] for e in result['graph']['edges']} == {'leaving','peer'}
    successor = tools.successor('leaving','window/core',since=since)['rows']
    assert next(row for row in successor if row['successor']=='oldauthor')['theirCommits'] == 1
    owners = tools.declared_vs_actual(since=since)['rows']
    assert next(row for row in owners if row['module']=='window')['actualTop3'] == ['leaving','peer']
    risk = tools._run('15b_refresh_component_risk', {'since':since}, graph=graph, include_graph=False)['rows']
    assert next(row for row in risk if row['component']=='window/core')['recentAuthors'] == 2


def test_reviewers_are_separate_qualified_ranked_and_graph_prs_capped(window_graph):
    graph, since = window_graph
    graph.query("""
        MATCH (c:Commit {sha:'leaving-0'}), (c2:Commit {sha:'leaving-1'})
        UNWIND range(1,4) AS n
        CREATE (pr:PR {number:10000+n})
        CREATE (c)-[:PART_OF]->(pr), (c2)-[:PART_OF]->(pr)
    """)
    reviewers = [{'login':f'review{i}', 'active':True, 'bot':False,'at':NOW,
                  'prs':4 if i==0 else 1} for i in range(7)]
    reviewers += [dict(login=login,active=active,bot=bot,at=at,prs=4)
                  for login,active,bot,at in [('inactive',False,False,NOW),
                      ('reviewbot',True,True,NOW),('stale',True,False,since-1),
                      ('boundary-review',True,False,since),('leaving',True,False,NOW)]]
    graph.query("""
        UNWIND $rows AS row
        MERGE (p:Person {login:row.login}) SET p.bot=row.bot
        FOREACH (_ IN CASE WHEN row.active THEN [1] ELSE [] END | SET p:Active)
        WITH row,p
        MATCH (pr:PR) WHERE pr.number > 10000 AND pr.number <= 10000+row.prs
        CREATE (p)-[:REVIEWED {at:row.at}]->(pr)
    """, {'rows':reviewers})
    # These reviews are fresh, but the only area commit is old, bulk, or deleted.
    graph.query("""
        UNWIND ['old-0','bulk','deleted','boundary'] AS sha
        MATCH (c:Commit {sha:sha})
        CREATE (:Person:Active {login:'invalid-'+sha,bot:false})-[:REVIEWED {at:$now}]->(pr:PR {number:sha})
        CREATE (c)-[:PART_OF]->(pr)
    """, {'now':NOW})
    result = tools.departure_impact('leaving',since=since)
    row = result['rows'][0]
    assert row['theirCommits'] == 3 and row['remaining'] == ['peer']
    assert row['risk'] == 'ONE OTHER AUTHOR'
    assert row['reviewerCount'] == 7
    assert row['reviewers'] == ['review0','review1','review2','review3','review4']
    nodes = {node['id']:node for node in result['graph']['nodes']}
    from collections import Counter
    reviewed = Counter(nodes[e['source']]['key'] for e in result['graph']['edges'] if e['type']=='REVIEWED')
    assert reviewed == {'review0':3,'review1':1,'review2':1,'review3':1,'review4':1}
    # With only the leaving author, review evidence still cannot change the author risk.
    graph.query("MATCH (p:Person {login:'peer'}) REMOVE p:Active")
    row = tools.departure_impact('leaving',since=since)['rows'][0]
    assert row['risk'] == 'NO OTHER AUTHOR' and row['reviewerCount'] == 7


def test_decision_confidence_partition_and_explicit_share_sort(graph):
    graph.query("""
        MATCH (alice:Person {login:'alice'}), (bob:Person {login:'bob'})
        CREATE (d:Decision {title:'Split',slug:'split'}),
               (p1:PR {number:991})-[:IMPLEMENTS {confidence:'high'}]->(d),
               (p1)-[:IMPLEMENTS {confidence:'low'}]->(d),
               (p2:PR {number:992})-[:IMPLEMENTS {confidence:'low'}]->(d),
               (p3:PR {number:993})-[:IMPLEMENTS {confidence:'high'}]->(d),
               (p4:PR {number:994})-[:IMPLEMENTS {confidence:'low'}]->(d),
               (alice)-[:OPENED]->(p1), (alice)-[:OPENED]->(p2),
               (bob)-[:OPENED]->(p3), (bob)-[:OPENED]->(p4),
               (guess:Decision {title:'Guess',slug:'guess'}),
               (p5:PR {number:995})-[:IMPLEMENTS {confidence:'low'}]->(guess),
               (alice)-[:OPENED]->(p5)
    """)
    rows = tools.decision_share('alice',minShare=0)['rows']
    row = next(row for row in rows if row['decision']=='Split')
    assert (row['theirExplicitPRs'],row['explicitPRs'],row['theirTitleMatchPRs'],row['titleMatchPRs']) == (1,2,1,2)
    for row in rows:
        assert row['theirExplicitPRs'] + row['theirTitleMatchPRs'] == row['theirPRs']
        assert row['explicitPRs'] + row['titleMatchPRs'] == row['totalPRs']
    assert [row['decision'] for row in rows].index('Split') < [row['decision'] for row in rows].index('Guess')
    high = tools.decision_share('alice',minShare=0,minConfidence='high')['rows']
    assert all(row['titleMatchPRs']==row['theirTitleMatchPRs']==0 for row in high)
    assert not any(row['decision']=='Split' for row in tools.decision_share('alice',minShare=0.6)['rows'])

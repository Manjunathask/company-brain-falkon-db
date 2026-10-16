"""Run the PLAN.md Cypher/runtime assumptions against a disposable bf_check graph."""

import os
import sys

from dotenv import load_dotenv
from falkordb import FalkorDB
from redis.exceptions import RedisError, ResponseError

from busfactor.db import ROOT, is_duplicate_index_error, load_query


GRAPH_NAME = "bf_check"
COPY_NAME = "bf_check_copy"


def _client() -> FalkorDB:
    load_dotenv(ROOT / ".env")
    return FalkorDB(
        host=os.getenv("FALKORDB_HOST", "127.0.0.1"),
        port=int(os.getenv("FALKORDB_PORT", "6379")),
        password=os.getenv("FALKORDB_PASSWORD") or None,
    )


def _check(label: str, operation) -> None:
    try:
        print(f"{label}: PASS — {operation()}")
    except Exception as exc:  # Each check reports independently for reviewer evidence.
        print(f"{label}: FAIL — {type(exc).__name__}: {exc}")


def main() -> int:
    try:
        client = _client()
        conn = client.connection
        conn.ping()
    except (RedisError, OSError, ConnectionError) as exc:
        print(f"FalkorDB unreachable: {exc}", file=sys.stderr)
        return 1

    # Start clean even if a previous interrupted run left the throwaway graph behind.
    try:
        conn.execute_command("GRAPH.DELETE", GRAPH_NAME)
    except ResponseError:
        pass
    try:
        conn.execute_command("GRAPH.DELETE", COPY_NAME)
    except ResponseError:
        pass
    graph = client.select_graph(GRAPH_NAME)

    try:
        def labels_check():
            graph.query("CREATE (:Person {login: 'check-a'}), (:Person {login: 'check-b'})")
            graph.query("MATCH (p:Person {login: 'check-a'}) SET p:Active")
            added = graph.query("MATCH (p:Active) RETURN count(p)").result_set[0][0]
            graph.query("MATCH (p:Person {login: 'check-a'}) REMOVE p:Active")
            removed = graph.query("MATCH (p:Active) RETURN count(p)").result_set[0][0]
            if added != 1 or removed != 0:
                raise AssertionError(f"Active count after SET={added}, after REMOVE={removed}")
            return f"Active count after SET={added}; after REMOVE={removed}"

        _check("a) Active labels", labels_check)

        def reduce_order_check():
            row = graph.query(
                "UNWIND [3, 1, 2] AS x WITH x ORDER BY x "
                "WITH collect(x) AS xs "
                "RETURN xs, reduce(acc = {n: 0, s: 0}, x IN xs | "
                "{n: acc.n + 1, s: acc.s + x}) AS summary"
            ).result_set[0]
            ordered, summary = row
            if ordered != [1, 2, 3] or summary != {"n": 3, "s": 6}:
                raise AssertionError(f"ordered={ordered}, summary={summary}")
            return f"collect={ordered}; reduce={summary}"

        _check("b) reduce/order", reduce_order_check)

        def foreach_check():
            graph.query("CREATE (:Commit {sha: 'check-commit'})")
            graph.query(
                "MATCH (c:Commit {sha: 'check-commit'}) "
                "OPTIONAL MATCH (pr:PR {number: -999}) "
                "FOREACH (_ IN CASE WHEN pr IS NULL THEN [] ELSE [1] END | "
                "MERGE (c)-[:PART_OF]->(pr))"
            )
            count = graph.query("MATCH (:Commit)-[r:PART_OF]->() RETURN count(r)").result_set[0][0]
            if count != 0:
                raise AssertionError(f"unexpected PART_OF count={count}")
            return "optional PR produced 0 PART_OF edges without error"

        _check("c) FOREACH/CASE", foreach_check)

        def copy_check():
            try:
                result = conn.execute_command("GRAPH.COPY", GRAPH_NAME, COPY_NAME)
                return f"GRAPH.COPY succeeded: {result!r}"
            except Exception as exc:
                raise AssertionError(f"GRAPH.COPY unavailable: {type(exc).__name__}: {exc}") from exc

        _check("d) GRAPH.COPY", copy_check)

        def algorithms_check():
            graph.query(
                "CREATE (a:Active:Person {login:'a'}), (b:Active:Person {login:'b'}), "
                "(c:Active:Person {login:'c'}), (a)-[:WORKS_WITH]->(b), (b)-[:WORKS_WITH]->(c)"
            )
            between = graph.query(
                "CALL algo.betweenness({nodeLabels: ['Active'], relationshipTypes: ['WORKS_WITH']}) "
                "YIELD node, score RETURN node.login, score"
            ).result_set
            components = graph.query(
                "CALL algo.WCC({nodeLabels: ['Active'], relationshipTypes: ['WORKS_WITH']}) "
                "YIELD node, componentId RETURN node.login, componentId"
            ).result_set
            if not between or not components:
                raise AssertionError(f"betweenness rows={len(between)}, WCC rows={len(components)}")
            return f"betweenness rows={len(between)}; WCC rows={len(components)}"

        _check("e) graph algorithms", algorithms_check)

        def version_check():
            modules = conn.execute_command("INFO", "MODULES")
            server = conn.execute_command("INFO", "SERVER")
            return f"INFO MODULES={modules!r}; INFO SERVER={server!r}"

        _check("f) server version/info", version_check)

        def duplicate_index_check():
            statement = next(
                line.strip()
                for line in load_query("00_indexes").splitlines()
                if line.strip() and not line.strip().startswith("//")
            )
            graph.query(statement)
            try:
                graph.query(statement)
            except ResponseError as exc:
                exact_error = str(exc)
                print(f"g) duplicate-index second-call error: {exact_error!r}")
                if not is_duplicate_index_error(exc):
                    raise AssertionError("db.create_indexes would not tolerate this error") from exc
                return f"db.create_indexes tolerates exact error {exact_error!r}"
            print("g) duplicate-index second-call error: <no error>")
            return "second CREATE INDEX succeeded; db.create_indexes would tolerate it"

        _check("g) duplicate index", duplicate_index_check)

        def clear_rebuild_check():
            # The algorithm check above creates WORKS_WITH edges; isolate this shape check from them.
            graph.query("MATCH (n) DETACH DELETE n")
            cases = (
                (
                    "KNOWS",
                    "(a:Person {login:'shape-owner'})",
                    "(m:Module {name:'shape-module'})",
                    "(a)-[:KNOWS]->(m)",
                    "MATCH (a:Person {login:'shape-owner'}), (m:Module {name:'shape-module'})",
                ),
                (
                    "WORKS_WITH",
                    "(a:Person {login:'shape-a'})",
                    "(b:Person {login:'shape-b'})",
                    "(a)-[:WORKS_WITH]->(b)",
                    "MATCH (a:Person {login:'shape-a'}), (b:Person {login:'shape-b'})",
                ),
            )
            evidence = []
            for rel_type, left_node, right_node, edge, endpoint_match in cases:
                graph.query(f"CREATE {left_node}, {right_node}")
                graph.query(f"MATCH {left_node}, {right_node} MERGE {edge}")
                clear_and_rebuild = (
                    f"OPTIONAL MATCH ()-[old:{rel_type}]->() DELETE old "
                    f"WITH count(old) AS cleared {endpoint_match} MERGE {edge} RETURN cleared"
                )
                with_edge = graph.query(clear_and_rebuild).result_set[0][0]
                after_existing = graph.query(
                    f"MATCH ()-[r:{rel_type}]->() RETURN count(r)"
                ).result_set[0][0]
                graph.query(f"MATCH ()-[r:{rel_type}]->() DELETE r")
                without_edge = graph.query(clear_and_rebuild).result_set[0][0]
                after_empty = graph.query(
                    f"MATCH ()-[r:{rel_type}]->() RETURN count(r)"
                ).result_set[0][0]
                if (with_edge, after_existing, without_edge, after_empty) != (1, 1, 0, 1):
                    raise AssertionError(
                        f"{rel_type}: cleared/count with edge={with_edge}/{after_existing}, "
                        f"empty={without_edge}/{after_empty}"
                    )
                evidence.append(
                    f"{rel_type} cleared/count existing=1/1, none=0/1"
                )
            return "; ".join(evidence)

        _check("h) OPTIONAL MATCH clear/rebuild", clear_rebuild_check)

        def reduce_null_check():
            row = graph.query(
                "WITH [10, null, 30, 20] AS times "
                "RETURN reduce(latest = null, at IN [x IN times WHERE x IS NOT NULL] | "
                "CASE WHEN latest IS NULL OR at > latest THEN at ELSE latest END)"
            ).result_set[0][0]
            if row != 30:
                raise AssertionError(f"latest={row}, expected 30")
            return f"filtered [10, null, 30, 20] to maximum {row}"

        _check("i) reduce over filtered nulls", reduce_null_check)
    finally:
        for graph_name in (COPY_NAME, GRAPH_NAME):
            try:
                conn.execute_command("GRAPH.DELETE", graph_name)
            except Exception as exc:
                print(f"cleanup {graph_name}: FAIL — {type(exc).__name__}: {exc}")
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

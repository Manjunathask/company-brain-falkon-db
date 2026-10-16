from pathlib import Path

import pytest

from busfactor.ingest.codeowners import parse_codeowners, rows_for_loading
from busfactor.ingest.git_log import parse_git_log
from busfactor.ingest.identity import load_api_map, normalize_login, resolve_person_key
from busfactor.ingest.rfcs import README, parse_rfcs
from busfactor.db import is_duplicate_index_error, load_query


def test_git_log_parses_binary_root_and_area():
    captured = (
        "\x1eabc123\x1f1730000000\x1f[SPARK] Improve reader (#42)\x1fUSER@EXAMPLE.COM\x1fA Person\n"
        "10\t2\tspark/src/Reader.scala\n-\t-\tbuild.sbt\n"
        "\x1edef456\x1f1730000001\x1fUpdate root docs\x1fother@example.com\x1fOther Person\n"
        "1\t0\tREADME.md\n"
    )
    commits = parse_git_log(captured)
    assert len(commits) == 2
    assert commits[0]["ts"] == 1730000000000
    assert commits[0]["area"] == "spark"
    assert commits[0]["pr"] == 42
    assert commits[0]["authorEmail"] == "user@example.com"
    assert commits[0]["files"][1] == {"path": "build.sbt", "module": "root", "added": 0, "deleted": 0}
    assert commits[1]["pr"] is None
    assert commits[1]["area"] is None
    assert commits[1]["files"][0]["module"] == "root"


def test_identity_resolution_precedence_and_noreply():
    assert resolve_person_key("A@EXAMPLE.COM", {"a@example.com": "from-api"}) == "from-api"
    assert resolve_person_key("12345+octocat@users.noreply.github.com") == "octocat"
    assert resolve_person_key("octocat@users.noreply.github.com") == "octocat"
    assert resolve_person_key("person@example.com") == "email:person@example.com"
    assert normalize_login("@TimothyW553") == "timothyw553"
    assert resolve_person_key("a@example.com", {"a@example.com": "TimothyW553"}) == "timothyw553"
    assert resolve_person_key("12345+TimothyW553@users.noreply.github.com") == "timothyw553"


def test_api_identity_map_keeps_null_as_unresolved(tmp_path, monkeypatch):
    import busfactor.ingest.identity as identity

    monkeypatch.setattr(identity, "ROOT", tmp_path)
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    (raw / "identities.json").write_text(
        '{"A@EXAMPLE.COM":"TimothyW553","nobody@example.com":null}',
        encoding="utf-8",
    )
    api_map = load_api_map()
    assert api_map == {"a@example.com": "TimothyW553", "nobody@example.com": None}
    assert resolve_person_key("a@example.com", api_map) == "timothyw553"
    assert resolve_person_key("nobody@example.com", api_map) == "email:nobody@example.com"


def test_rfcs_from_real_readme_when_available():
    if not README.exists():
        pytest.skip("Delta clone is unavailable")
    rows = parse_rfcs(README.read_text(encoding="utf-8"))
    assert len(rows) == 19
    assert sum(row["status"] == "proposed" for row in rows) == 11
    assert next(row for row in rows if row["slug"] == "column-mapping-usage-tracking")["path"] == "protocol_rfcs/column-mapping-usage-tracking.md"
    assert next(row for row in rows if row["status"] == "proposed")["decidedOn"] is None


def test_codeowners_parse_and_real_rule_count():
    source = "/* @one\n/build.sbt @two @three\n/spark/v2/ @maintainer\n"
    rows = parse_codeowners(source)
    assert rows[0] == {"pattern": "/*", "module": "root", "owners": ["one"]}
    assert rows[1]["module"] == "root"
    assert rows[2]["module"] == "spark"
    normalized = rows_for_loading(parse_codeowners("/spark/ @TimothyW553\n"))[0]
    assert normalized["owners"] == [{"login": "timothyw553", "handle": "TimothyW553"}]
    codeowners = Path("data/delta/.github/CODEOWNERS")
    if codeowners.exists():
        assert len(parse_codeowners(codeowners.read_text(encoding="utf-8"))) == 9


def test_load_query_reads_known_cypher():
    query = load_query("01_load_commits")
    assert "UNWIND $rows AS c" in query
    assert "MERGE (c)-[:PART_OF]" not in query
    with pytest.raises(ValueError):
        load_query("../AGENTS")


def test_duplicate_index_error_rule_matches_only_falkordb_duplicate_message():
    assert is_duplicate_index_error(Exception("Attribute 'login' is already indexed"))
    assert not is_duplicate_index_error(Exception("permission denied"))

import re

from busfactor.derive import QUERY_NAMES, build_query_params
from busfactor.db import load_query


def test_all_derive_queries_have_headers_and_declared_parameters():
    params_by_query = build_query_params(since=1, min_shared=3, max_file_commits=150)
    for name in QUERY_NAMES:
        query = load_query(name)
        header = "\n".join(query.splitlines()[:3])
        assert "// Answers:" in header, name
        assert "// Parameters:" in header, name
        actual_params = set(re.findall(r"\$([A-Za-z_][A-Za-z0-9_]*)", query))
        assert actual_params == set(params_by_query[name]), name


def test_every_derive_query_file_is_registered():
    from busfactor.db import ROOT

    files = {path.stem for path in (ROOT / "queries").glob("0[34]*_derive*.cypher")}
    assert files == set(QUERY_NAMES) | {
        "04d_derive_implements_issue_ref",
        "04e_derive_implements_rfc_doc",
    }


def test_every_query_file_has_header_and_declares_exact_parameters():
    from busfactor.db import ROOT

    for path in sorted((ROOT / "queries").glob("*.cypher")):
        query = path.read_text(encoding="utf-8")
        header = "\n".join(query.splitlines()[:3])
        assert "// Answers:" in header, path.name
        assert "// Parameters:" in header, path.name
        declared = set(re.findall(r"\$([A-Za-z_][A-Za-z0-9_]*)", header))
        actual = set(re.findall(r"\$([A-Za-z_][A-Za-z0-9_]*)", query))
        assert actual == declared, path.name

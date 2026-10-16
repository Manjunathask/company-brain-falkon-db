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
    assert files == set(QUERY_NAMES)

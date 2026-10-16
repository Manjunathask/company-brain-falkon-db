import json
from pathlib import Path

from busfactor.ingest import github_api
from busfactor.ingest.github_api import GitHubGraphQL, _identity_map, _pr_rows, parse_pr, references
from busfactor.ingest.identity import is_bot

FIXTURES = Path(__file__).parent / "fixtures" / "github"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_pr_pagination_stops_at_git_since(monkeypatch, tmp_path):
    monkeypatch.setattr(github_api, "RAW", tmp_path)
    monkeypatch.setattr(github_api, "_git_commits", lambda: [])

    class FakeAPI:
        def __init__(self):
            self.calls = []

        def _request(self, query, cache_path):
            self.calls.append(query)
            return fixture("prs_page.json")

    api = FakeAPI()
    rows = _pr_rows(api, "2024-10-15")
    assert [row["number"] for row in rows] == [90]
    assert len(api.calls) == 1
    assert "pullRequests(first:25" in api.calls[0]


def test_identity_alias_batch_preserves_null_login(monkeypatch, tmp_path):
    monkeypatch.setattr(github_api, "RAW", tmp_path)
    monkeypatch.setattr(github_api, "_git_commits", lambda: [
        {"authorEmail": "Alice@Example.com", "sha": "sha-a"},
        {"authorEmail": "unknown@example.com", "sha": "sha-b"},
    ])

    class FakeAPI:
        def _request(self, query, cache_path, **kwargs):
            assert "c0: object(oid:\"sha-a\")" in query
            assert "c1: object(oid:\"sha-b\")" in query
            return fixture("identities_batch.json")

    assert _identity_map(FakeAPI()) == {
        "alice@example.com": "AliceGH", "unknown@example.com": None,
    }
    assert json.loads((tmp_path / "identities.json").read_text())[
        "unknown@example.com"
    ] is None


def test_pr_reviewers_are_distinct_and_exclude_author():
    row = parse_pr({
        "number": 1, "title": "T", "state": "OPEN", "createdAt": "2026-10-16T00:00:00Z",
        "mergedAt": None, "body": "", "author": {"login": "Owner"},
        "reviews": {"nodes": [
            {"author": {"login": "Reviewer"}},
            {"author": {"login": "reviewer"}},
            {"author": {"login": "OWNER"}},
            {"author": {"login": "dependabot[bot]"}},
        ]},
    })
    assert row["author"] == "owner"
    assert row["reviewers"] == [
        {"login": "reviewer", "handle": "Reviewer", "bot": False},
        {"login": "dependabot[bot]", "handle": "dependabot[bot]", "bot": True},
    ]


def test_deleted_author_maps_to_ghost_bot():
    row = parse_pr({
        "number": 2, "title": "T", "state": "CLOSED", "createdAt": "2026-10-16T00:00:00Z",
        "mergedAt": None, "body": "", "author": None, "reviews": {"nodes": []},
    })
    assert (row["author"], row["authorHandle"], row["authorBot"]) == ("ghost", "ghost", True)
    assert is_bot("GitHub-Actions") and is_bot("ghost") and is_bot("custom[bot]")


def test_references_supports_github_forms_without_substring_false_positives():
    body = "Fixes #4381, closes delta-io/delta#4382 and https://github.com/delta-io/delta/issues/4383. Also #1a and issue 4384. PR: https://github.com/delta-io/delta/pull/4385"
    assert references(body) == {4381, 4382, 4383, 4385}


def test_cache_hit_does_not_call_http(tmp_path):
    cache = tmp_path / "cached.json"
    cache.write_text(json.dumps({"data": {"rateLimit": {"remaining": 100, "resetAt": None}, "ok": True}}))

    class NoHTTP:
        def post(self, *args, **kwargs):
            raise AssertionError("cache hit made an HTTP call")

    api = GitHubGraphQL("test-token", client=NoHTTP())
    assert api._request("query { ok }", cache) == json.loads(cache.read_text())


class FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class ResponseQueue:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = 0

    def post(self, *args, **kwargs):
        self.calls += 1
        return FakeResponse(self.payloads.pop(0))


def test_retryable_graphql_error_retries_then_caches_success(tmp_path, monkeypatch):
    monkeypatch.setattr(github_api.time, "sleep", lambda _: None)
    transient = {"errors": [{"type": "RATE_LIMITED", "message": "rate limited"}]}
    success = {"data": {"rateLimit": {"remaining": 100, "resetAt": None}, "ok": True}}
    client = ResponseQueue([transient, success])
    cache = tmp_path / "request.json"
    assert GitHubGraphQL("token", client=client)._request("query { ok }", cache)["data"]["ok"]
    assert client.calls == 2
    assert json.loads(cache.read_text()) == success


def test_not_found_alias_batch_keeps_partial_response_and_caches(tmp_path, capsys):
    partial = {
        "data": {"rateLimit": {"remaining": 100, "resetAt": None}, "repository": {"p1": {"number": 1}, "p2": None}},
        "errors": [{"type": "NOT_FOUND", "message": "Could not resolve pull request", "path": ["repository", "p2"]}],
    }
    client = ResponseQueue([partial])
    cache = tmp_path / "alias.json"
    result = GitHubGraphQL("token", client=client)._request(
        "query { aliases }", cache, allow_not_found=True, context_aliases={"p1": 1, "p2": 2}
    )
    assert result["data"]["repository"]["p1"]["number"] == 1
    assert client.calls == 1
    assert json.loads(cache.read_text()) == partial
    assert "[2]" in capsys.readouterr().err


def test_unexpected_graphql_error_is_not_cached(tmp_path):
    client = ResponseQueue([{"data": {"ok": None}, "errors": [{"type": "FORBIDDEN", "message": "forbidden"}]}])
    cache = tmp_path / "failure.json"
    try:
        GitHubGraphQL("token", client=client)._request("query { ok }", cache)
    except RuntimeError as exc:
        assert "FORBIDDEN" in str(exc)
    else:
        raise AssertionError("expected GraphQL error")
    assert not cache.exists()

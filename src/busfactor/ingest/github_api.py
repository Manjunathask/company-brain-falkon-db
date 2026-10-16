"""Fetch and cache the public delta-io/delta GraphQL data used by the graph."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import time

import httpx
from dotenv import load_dotenv

from busfactor.db import ROOT, batched
from busfactor.ingest.identity import is_bot, normalize_login

API_URL = "https://api.github.com/graphql"
RAW = ROOT / "data" / "raw"
MAX_TRIES = 5
_LAST_REMAINING = None
_REF_RE = re.compile(
    r"(?<![\w])(?:delta-io/delta#|#)(\d+)(?!\w)|"
    r"(?<![\w])https://github\.com/delta-io/delta/(?:issues|pull)/(\d+)(?!\w)",
    re.IGNORECASE,
)


def references(pr_body: str | None) -> set[int]:
    """Return Delta issue/PR numbers cited using a supported GitHub reference."""
    return {int(a or b) for a, b in _REF_RE.findall(pr_body or "")}


def _epoch_ms(value: str | None) -> int | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return int(parsed.astimezone(timezone.utc).timestamp() * 1000)


def _person(raw: dict | None, *, placeholder: bool = False) -> tuple[str, str]:
    if not raw or not raw.get("login"):
        return ("ghost", "ghost") if placeholder else ("", "")
    handle = raw["login"]
    return normalize_login(handle), handle


def parse_pr(raw: dict) -> dict:
    author, author_handle = _person(raw.get("author"), placeholder=True)
    reviewers, seen = [], set()
    for review in raw.get("reviews", {}).get("nodes", []):
        login, handle = _person(review.get("author"))
        if login and login != author and login not in seen:
            reviewers.append({"login": login, "handle": handle, "bot": is_bot(login)})
            seen.add(login)
    return {
        "number": int(raw["number"]), "title": raw.get("title") or "",
        "state": raw.get("state"), "createdAt": _epoch_ms(raw.get("createdAt")),
        "mergedAt": _epoch_ms(raw.get("mergedAt")), "body": raw.get("body") or "",
        "author": author, "authorHandle": author_handle,
        "authorBot": is_bot(author), "reviewers": reviewers,
    }


def parse_issue(raw: dict) -> dict:
    author, author_handle = _person(raw.get("author"), placeholder=True)
    commenters, seen = [], set()
    for comment in raw.get("comments", {}).get("nodes", []):
        login, handle = _person(comment.get("author"))
        if login and login not in seen:
            commenters.append({"login": login, "handle": handle, "bot": is_bot(login)})
            seen.add(login)
    return {
        "number": int(raw["number"]), "title": raw.get("title") or "",
        "state": raw.get("state"), "createdAt": _epoch_ms(raw.get("createdAt")),
        "author": author, "authorHandle": author_handle,
        "authorBot": is_bot(author), "commenters": commenters,
    }


def _connection_nodes(connection: dict) -> list[dict]:
    return connection.get("nodes", []) if connection else []


class GitHubGraphQL:
    def __init__(self, token: str, refresh: bool = False, client=None):
        self.token = token
        self.refresh = refresh
        self.client = client or httpx.Client(timeout=60)
        self.remaining = None

    @staticmethod
    def _error_type(error: dict) -> str | None:
        return error.get("type") or error.get("extensions", {}).get("type") or error.get("extensions", {}).get("code")

    @classmethod
    def _is_retryable_graphql_error(cls, error: dict) -> bool:
        kind = cls._error_type(error)
        message = error.get("message", "").lower()
        return kind == "RATE_LIMITED" or any(
            phrase in message for phrase in ("secondary rate limit", "timeout", "something went wrong")
        )

    def _request(self, query: str, cache_path: Path, *, allow_not_found=False, context_aliases=None) -> dict:
        payload = None
        if cache_path.exists() and not self.refresh:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            cached_errors = cached.get("errors", [])
            retryable = any(self._is_retryable_graphql_error(error) for error in cached_errors)
            only_not_found = bool(cached_errors) and all(self._error_type(error) == "NOT_FOUND" for error in cached_errors)
            if not cached_errors or (allow_not_found and only_not_found):
                payload = cached
                if only_not_found:
                    self._log_not_found(cached_errors, context_aliases)
            else:
                cache_path.unlink()
                if not retryable:
                    raise RuntimeError(f"GitHub GraphQL errors: {cached_errors}")
        if payload is None:
            for attempt in range(MAX_TRIES):
                response = self.client.post(
                    API_URL,
                    headers={"Authorization": f"bearer {self.token}"},
                    json={"query": query},
                )
                if response.status_code in (502, 503):
                    if attempt == MAX_TRIES - 1:
                        response.raise_for_status()
                    time.sleep(2 ** attempt)
                    continue
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    secondary = "secondary rate limit" in exc.response.text.lower()
                    if (exc.response.status_code == 429 or secondary) and attempt < MAX_TRIES - 1:
                        time.sleep(2 ** attempt)
                        continue
                    raise
                payload = response.json()
                errors = payload.get("errors", [])
                transient = [error for error in errors if self._is_retryable_graphql_error(error)]
                if transient:
                    if attempt == MAX_TRIES - 1:
                        raise RuntimeError(f"GitHub GraphQL transient errors after {MAX_TRIES} tries: {transient}")
                    time.sleep(2 ** attempt)
                    continue
                # Cache only successful responses or tolerated NOT_FOUND alias batches.
                only_not_found = bool(errors) and all(self._error_type(error) == "NOT_FOUND" for error in errors)
                if errors and not (allow_not_found and only_not_found):
                    raise RuntimeError(f"GitHub GraphQL errors: {errors}")
                if only_not_found:
                    self._log_not_found(errors, context_aliases)
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
                break
            if payload is None:
                raise RuntimeError("GitHub GraphQL request failed after retries")
        errors = payload.get("errors", [])
        tolerated_not_found = allow_not_found and bool(errors) and all(
            self._error_type(error) == "NOT_FOUND" for error in errors
        )
        if errors and not tolerated_not_found:
            raise RuntimeError(f"GitHub GraphQL errors: {errors}")
        limit = payload.get("data", {}).get("rateLimit") or {}
        self.remaining = limit.get("remaining", self.remaining)
        if self.remaining is not None and self.remaining < 50:
            reset_at = limit.get("resetAt")
            if reset_at:
                reset = datetime.fromisoformat(reset_at.replace("Z", "+00:00"))
                time.sleep(max(0, (reset - datetime.now(timezone.utc)).total_seconds()))
        return payload

    @staticmethod
    def _log_not_found(errors: list[dict], context_aliases: dict | None) -> None:
        missing_aliases = {
            str(error["path"][-1])
            for error in errors
            if error.get("path") and str(error["path"][-1]) in (context_aliases or {})
        }
        details = [context_aliases[key] for key in sorted(missing_aliases)] if context_aliases else []
        print(f"GitHub GraphQL NOT_FOUND; missing aliases: {details}", file=sys.stderr)


def _git_commits() -> list[dict]:
    path = RAW / "git_log.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}; run git log ingestion first")
    return json.loads(path.read_text(encoding="utf-8"))


def _rfc_numbers() -> list[int]:
    path = RAW / "rfcs.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}; run RFC ingestion first")
    return sorted({int(row["issue"]) for row in json.loads(path.read_text(encoding="utf-8"))})


PR_FIELDS = "number title state createdAt mergedAt body author { login } reviews(first: 30) { nodes { author { login } state submittedAt } }"
ISSUE_FIELDS = "number title state createdAt author { login } comments(first: 100) { nodes { author { login } createdAt } pageInfo { hasNextPage endCursor } }"


def _pr_rows(api: GitHubGraphQL, since: str) -> list[dict]:
    query_since = datetime.fromisoformat(since).replace(tzinfo=timezone.utc)
    cursor = None
    fetched: dict[int, dict] = {}
    page = 0
    while True:
        after = f', after: "{cursor}"' if cursor else ""
        query = f'''query {{ rateLimit {{ cost remaining resetAt }} repository(owner:"delta-io", name:"delta") {{ pullRequests(first:25, orderBy:{{field: CREATED_AT, direction: DESC}}{after}) {{ nodes {{ {PR_FIELDS} }} pageInfo {{ hasNextPage endCursor }} }} }} }}'''
        payload = api._request(query, RAW / "github" / "prs" / f"page-{page}.json")
        connection = payload["data"]["repository"]["pullRequests"]
        stop = False
        for raw in _connection_nodes(connection):
            created = datetime.fromisoformat(raw["createdAt"].replace("Z", "+00:00"))
            if created < query_since:
                stop = True
                break
            fetched[int(raw["number"])] = raw
        if stop or not connection["pageInfo"]["hasNextPage"]:
            break
        cursor = connection["pageInfo"]["endCursor"]
        page += 1

    referenced = {int(c["pr"]) for c in _git_commits() if c.get("pr") is not None}
    missing = sorted(referenced - fetched.keys())
    for batch_num, numbers in enumerate(batched(missing, 40)):
        aliases = " ".join(f"p{n}: pullRequest(number:{n}) {{ {PR_FIELDS} }}" for n in numbers)
        query = f'''query {{ rateLimit {{ cost remaining resetAt }} repository(owner:"delta-io", name:"delta") {{ {aliases} }} }}'''
        payload = api._request(
            query,
            RAW / "github" / "prs" / f"referenced-{batch_num}.json",
            allow_not_found=True,
            context_aliases={f"p{number}": number for number in numbers},
        )
        for number in numbers:
            raw = payload["data"]["repository"].get(f"p{number}")
            if raw:
                fetched[number] = raw
    return [parse_pr(fetched[n]) for n in sorted(fetched)]


def _identity_map(api: GitHubGraphQL) -> dict[str, str | None]:
    commits = _git_commits()
    by_email = {}
    for commit in commits:
        by_email.setdefault(commit["authorEmail"].strip().lower(), commit["sha"])
    result = {}
    for batch_num, entries in enumerate(batched(by_email.items(), 50)):
        aliases = " ".join(
            f'c{i}: object(oid:"{sha}") {{ ... on Commit {{ author {{ email user {{ login }} }} }} }}'
            for i, (_, sha) in enumerate(entries)
        )
        query = f'''query {{ rateLimit {{ cost remaining resetAt }} repository(owner:"delta-io", name:"delta") {{ {aliases} }} }}'''
        payload = api._request(
            query,
            RAW / "github" / "identities" / f"batch-{batch_num}.json",
            allow_not_found=True,
            context_aliases={f"c{i}": email for i, (email, _) in enumerate(entries)},
        )
        objects = payload["data"]["repository"]
        for i, (email, _) in enumerate(entries):
            author = (objects.get(f"c{i}") or {}).get("author") or {}
            user = author.get("user") or {}
            result[email] = user.get("login")
    # Persist normalized email keys and original API spelling; identity.py normalizes on use.
    (RAW / "identities.json").parent.mkdir(parents=True, exist_ok=True)
    (RAW / "identities.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def _issue_rows(api: GitHubGraphQL) -> list[dict]:
    rows = []
    for number in _rfc_numbers():
        after = None
        comments = []
        page = 0
        raw_issue = None
        while True:
            cursor = f', after: "{after}"' if after else ""
            query = f'''query {{ rateLimit {{ cost remaining resetAt }} repository(owner:"delta-io", name:"delta") {{ issue(number:{number}) {{ {ISSUE_FIELDS.replace("comments(first: 100)", f"comments(first: 100{cursor})")} }} }} }}'''
            payload = api._request(query, RAW / "github" / "rfc_issues" / f"issue-{number}-page-{page}.json")
            raw_issue = payload["data"]["repository"]["issue"]
            if not raw_issue:
                break
            connection = raw_issue.get("comments", {})
            comments.extend(connection.get("nodes", []))
            page_info = connection.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            after = page_info["endCursor"]
            page += 1
        if raw_issue:
            raw_issue["comments"] = {"nodes": comments}
            rows.append(parse_issue(raw_issue))
    return rows


def fetch(kind: str, refresh: bool = False) -> list[dict] | dict:
    global _LAST_REMAINING
    load_dotenv(ROOT / ".env")
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN not set (set it in .env or the environment)")
    api = GitHubGraphQL(token, refresh=refresh)
    if kind == "identities":
        result = _identity_map(api)
    elif kind == "prs":
        result = _pr_rows(api, os.getenv("GIT_SINCE", "2024-10-15"))
        _write_rows("prs.json", result)
    elif kind == "rfc_issues":
        result = _issue_rows(api)
        _write_rows("rfc_issues.json", result)
    else:
        raise ValueError(f"unknown GitHub data kind: {kind}")
    _LAST_REMAINING = api.remaining
    return result


def _write_rows(name: str, rows: list[dict]) -> None:
    (RAW / name).parent.mkdir(parents=True, exist_ok=True)
    (RAW / name).write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch cached GitHub data for Bus Factor")
    parser.add_argument("kind", choices=["identities", "prs", "rfc_issues", "all"])
    parser.add_argument("--refresh", action="store_true", help="ignore cached GraphQL responses")
    args = parser.parse_args(argv)
    kinds = ["identities", "prs", "rfc_issues"] if args.kind == "all" else [args.kind]
    try:
        for kind in kinds:
            result = fetch(kind, args.refresh)
            count = len(result)
            print(f"{kind}: {count}")
        print(f"rate limit remaining: {_LAST_REMAINING if _LAST_REMAINING is not None else 'unknown'}")
    except (RuntimeError, FileNotFoundError, httpx.HTTPError, KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

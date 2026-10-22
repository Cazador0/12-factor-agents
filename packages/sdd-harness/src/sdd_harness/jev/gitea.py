"""The small slice of the Gitea 28.x REST API Jev uses, checked against the v28.2.0 source.

Facts this client relies on (docs/research/reports/Jev watchdog for coding agents.md):

- ``GET /commits/{sha}/status`` combines only the returned page (default 30, max 50); the true count is the
  ``X-Total-Count`` header, so larger sets are re-read from ``/statuses`` and combined here. A ``CommitStatus``
  carries its state under ``status``; ``CombinedStatus`` uses ``state``.
- Gitea Actions maps a cancelled job to ``failure``; the run list's ``conclusion`` tells the two apart.
- ``GET /issues/{index}/comments`` does not paginate; ``POST`` creates, ``PATCH /issues/comments/{id}`` edits.
- ``POST /issues/{index}/labels`` takes IDs or names, never mixed; unknown names are dropped silently, and
  removal takes an ID — so Jev always works in IDs, adds with POST and never replaces with PUT.
- ``GET /branches/{name}`` reports ``user_can_push`` and ``user_can_merge`` for the caller: Jev refuses to run if
  either is true.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Protocol

from .models import CommitCI

FAILING = {"error", "failure", "warning"}
PAGE = 50


class GiteaError(RuntimeError):
    """Gitea could not be read or written; the scan becomes ``unknown`` rather than guessing."""


class GiteaClient(Protocol):
    def me(self) -> str: ...
    def version(self) -> str: ...
    def default_branch(self, owner: str, repo: str) -> str: ...
    def branch_rights(self, owner: str, repo: str, branch: str) -> tuple[bool, bool]: ...
    def branch_commits(self, owner: str, repo: str, branch: str, limit: int) -> list[dict]: ...
    def commit_statuses(self, owner: str, repo: str, sha: str) -> list[dict]: ...
    def runs_for_commit(self, owner: str, repo: str, sha: str) -> list[dict]: ...
    def list_comments(self, owner: str, repo: str, issue: int) -> list[dict]: ...
    def create_comment(self, owner: str, repo: str, issue: int, body: str) -> int: ...
    def edit_comment(self, owner: str, repo: str, comment_id: int, body: str) -> None: ...
    def repo_labels(self, owner: str, repo: str) -> list[dict]: ...
    def add_labels(self, owner: str, repo: str, issue: int, label_ids: list[int]) -> list[int]: ...
    def remove_label(self, owner: str, repo: str, issue: int, label_id: int) -> None: ...


def combine(statuses: list[dict]) -> str:
    """Gitea's combine rule over the latest status per context: any failure wins, then pending, else success.

    ``skipped`` counts as success; no statuses at all is reported as ``none`` (Gitea says ``pending`` with a zero
    count, which means "no CI reported", not "running").
    """
    latest: dict[str, str] = {}
    for s in statuses:  # newest first
        ctx = s.get("context", "")
        if ctx not in latest:
            latest[ctx] = str(s.get("status") or s.get("state") or "").lower()
    if not latest:
        return "none"
    states = set(latest.values())
    if states & FAILING:
        return "failure"
    if "pending" in states:
        return "pending"
    return "success"


def failing_contexts(statuses: list[dict]) -> frozenset[str]:
    latest: dict[str, str] = {}
    for s in statuses:
        ctx = s.get("context", "")
        if ctx not in latest:
            latest[ctx] = str(s.get("status") or s.get("state") or "").lower()
    return frozenset(c for c, st in latest.items() if st in FAILING)


def commit_outcome(client: GiteaClient, owner: str, repo: str, sha: str) -> CommitCI:
    statuses = client.commit_statuses(owner, repo, sha)
    outcome = combine(statuses)
    failing = failing_contexts(statuses)
    if outcome == "failure":
        runs = client.runs_for_commit(owner, repo, sha)
        concluded = [str(r.get("conclusion") or "").lower() for r in runs if r.get("conclusion")]
        bad = [c for c in concluded if c in ("failure", "cancelled")]
        if bad and all(c == "cancelled" for c in bad):
            return CommitCI(sha, "cancelled", failing)
    return CommitCI(sha, outcome, failing)  # type: ignore[arg-type]


def label_ids(client: GiteaClient, owner: str, repo: str, names: list[str]) -> dict[str, int]:
    """Resolve label names to IDs once; missing labels are reported, never created (people create labels)."""
    have = {str(lbl["name"]): int(lbl["id"]) for lbl in client.repo_labels(owner, repo)}
    return {n: have[n] for n in names if n in have}


def marker(key: str) -> str:
    return f"<!-- jev:{key} -->"


def find_comment(client: GiteaClient, owner: str, repo: str, issue: int, key: str, login: str) -> int | None:
    """Jev's own comment carrying ``key``'s marker, if one exists (comments are listed in full; no paging)."""
    tag = marker(key)
    for c in client.list_comments(owner, repo, issue):
        if tag in str(c.get("body", "")) and (c.get("user") or {}).get("login") == login:
            return int(c["id"])
    return None


def self_check(client: GiteaClient, repos: set[tuple[str, str]]) -> str:
    """Refuse to run with push or merge rights: Jev comments and labels, nothing more. Returns the bot login."""
    login = client.me()
    for owner, repo in sorted(repos):
        branch = client.default_branch(owner, repo)
        can_push, can_merge = client.branch_rights(owner, repo, branch)
        if can_push or can_merge:
            raise PermissionError(
                f"Jev's account {login!r} can {'push' if can_push else 'merge'} on {owner}/{repo}:{branch}; "
                "give it a team with code read, issues write, pulls write, actions read only"
            )
    return login


class HttpGiteaClient:
    """Token-authenticated REST client (scopes read:repository, write:issue; read:organization for org labels)."""

    def __init__(self, base_url: str, token: str, timeout: float = 20.0):
        self.base = base_url.rstrip("/") + "/api/v1"
        self.token = token
        self.timeout = timeout

    def _request(self, method: str, path: str, body: Any = None, query: dict | None = None) -> tuple[Any, dict]:
        url = self.base + path + (("?" + urllib.parse.urlencode(query)) if query else "")
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"token {self.token}")
        req.add_header("Accept", "application/json")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                headers = {k.lower(): v for k, v in resp.headers.items()}
        except urllib.error.HTTPError as exc:
            raise GiteaError(f"{method} {path} → HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise GiteaError(f"{method} {path} → {exc}") from exc
        return (json.loads(raw) if raw else None), headers

    def _get(self, path: str, query: dict | None = None) -> Any:
        return self._request("GET", path, query=query)[0]

    def _paged(self, path: str, query: dict | None = None) -> list[dict]:
        out: list[dict] = []
        page = 1
        while True:
            batch = self._get(path, {**(query or {}), "limit": PAGE, "page": page}) or []
            out += batch
            if len(batch) < PAGE:
                return out
            page += 1

    def me(self) -> str:
        return str(self._get("/user")["login"])

    def version(self) -> str:
        return str(self._get("/version")["version"])

    def default_branch(self, owner: str, repo: str) -> str:
        return str(self._get(f"/repos/{owner}/{repo}")["default_branch"])

    def branch_rights(self, owner: str, repo: str, branch: str) -> tuple[bool, bool]:
        b = self._get(f"/repos/{owner}/{repo}/branches/{urllib.parse.quote(branch, safe='')}")
        return bool(b.get("user_can_push")), bool(b.get("user_can_merge"))

    def branch_commits(self, owner: str, repo: str, branch: str, limit: int) -> list[dict]:
        rows = self._get(f"/repos/{owner}/{repo}/commits", {"sha": branch, "limit": limit, "stat": "false"}) or []
        return [
            {"sha": r["sha"], "created": r.get("created") or (r.get("commit") or {}).get("committer", {}).get("date")}
            for r in rows
        ]

    def commit_statuses(self, owner: str, repo: str, sha: str) -> list[dict]:
        body, headers = self._request("GET", f"/repos/{owner}/{repo}/commits/{sha}/status", query={"limit": PAGE})
        statuses = (body or {}).get("statuses") or []
        total = int(headers.get("x-total-count", len(statuses)) or 0)
        if total <= len(statuses):
            return statuses
        return self._paged(f"/repos/{owner}/{repo}/commits/{sha}/statuses", {"sort": "highestindex"})

    def runs_for_commit(self, owner: str, repo: str, sha: str) -> list[dict]:
        body = self._get(f"/repos/{owner}/{repo}/actions/runs", {"head_sha": sha, "limit": PAGE}) or {}
        return [r for r in body.get("workflow_runs", []) if r.get("head_sha") == sha]

    def list_comments(self, owner: str, repo: str, issue: int) -> list[dict]:
        return self._get(f"/repos/{owner}/{repo}/issues/{issue}/comments") or []

    def create_comment(self, owner: str, repo: str, issue: int, body: str) -> int:
        return int(self._request("POST", f"/repos/{owner}/{repo}/issues/{issue}/comments", {"body": body})[0]["id"])

    def edit_comment(self, owner: str, repo: str, comment_id: int, body: str) -> None:
        self._request("PATCH", f"/repos/{owner}/{repo}/issues/comments/{comment_id}", {"body": body})

    def repo_labels(self, owner: str, repo: str) -> list[dict]:
        return self._paged(f"/repos/{owner}/{repo}/labels")

    def add_labels(self, owner: str, repo: str, issue: int, label_ids: list[int]) -> list[int]:
        body = self._request("POST", f"/repos/{owner}/{repo}/issues/{issue}/labels", {"labels": label_ids})[0] or []
        return [int(lbl["id"]) for lbl in body]

    def remove_label(self, owner: str, repo: str, issue: int, label_id: int) -> None:
        self._request("DELETE", f"/repos/{owner}/{repo}/issues/{issue}/labels/{label_id}")

"""The small slice of the Gitea 28.x REST API Jev uses, checked against the v28.2.0 source.

Facts this client relies on (docs/research/reports/Jev watchdog for coding agents.md, re-checked in the source):

- List endpoints page with ``page``/``limit``, clamp ``limit`` silently to ``[api] MAX_RESPONSE_ITEMS`` and report the
  true size in ``X-Total-Count``; Jev reads until that count (or an empty page), never trusting a short page.
- ``GET /commits/{sha}/statuses`` lists every status (default order ``created_unix DESC``; ``sort=highestindex`` is
  oldest first). Jev keeps the status with the highest ``id`` per context, so server order never matters. A
  ``CommitStatus`` carries its state under ``status``; ``CombinedStatus`` uses ``state``.
- Gitea Actions maps a cancelled job to a ``failure`` status whose description reads "Canceled after …"
  (``services/actions/commit_status.go``), so cancellation is read per context from the status itself; failures
  from external CI still count.
- ``GET /repos/{o}/{r}/commits?sha=<branch>`` answers 404 for a branch not pushed yet: no commits, no CI.
- ``GET /issues/{index}/comments`` does not paginate; ``POST`` creates, ``PATCH /issues/comments/{id}`` edits and
  answers 404 once a person deleted the comment.
- ``POST /issues/{index}/labels`` takes IDs or names, never mixed; unknown names are dropped silently, so Jev always
  works in IDs (repository and organisation labels), adds with POST and never replaces with PUT. ``DELETE`` of a label
  the issue does not carry succeeds, so clearing labels can be retried.
- On a protected branch ``user_can_push``/``user_can_merge`` come from the protection rule, not the account's rights,
  so the self-check also reads the repository's ``permissions`` (push, admin).
- ``GET /user`` needs the ``read:user`` token scope.
"""

from __future__ import annotations

import http.client
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Protocol

from .models import CommitCI

FAILING = {"error", "failure", "warning"}
CANCELLED_PREFIXES = ("canceled", "cancelled")  # Gitea Actions: "Canceled after 1m2s" on a failure status
PAGE = 50
MAX_PAGES = 100  # a server that ignores ``page`` must not loop forever


class GiteaError(RuntimeError):
    """Gitea could not be read or written; the scan becomes ``unknown`` rather than guessing."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class GiteaClient(Protocol):
    def me(self) -> str: ...
    def version(self) -> str: ...
    def repo_info(self, owner: str, repo: str) -> dict: ...
    def branch_rights(self, owner: str, repo: str, branch: str) -> tuple[bool, bool]: ...
    def branch_commits(self, owner: str, repo: str, branch: str, limit: int) -> list[dict]: ...
    def commit_statuses(self, owner: str, repo: str, sha: str) -> list[dict]: ...
    def list_comments(self, owner: str, repo: str, issue: int) -> list[dict]: ...
    def create_comment(self, owner: str, repo: str, issue: int, body: str) -> int: ...
    def edit_comment(self, owner: str, repo: str, comment_id: int, body: str) -> None: ...
    def repo_labels(self, owner: str, repo: str) -> list[dict]: ...
    def org_labels(self, owner: str) -> list[dict]: ...
    def add_labels(self, owner: str, repo: str, issue: int, label_ids: list[int]) -> list[int]: ...
    def remove_label(self, owner: str, repo: str, issue: int, label_id: int) -> None: ...


def latest_per_context(statuses: list[dict]) -> dict[str, dict]:
    """The newest status of each context: the highest ``id`` wins; without ids, the first one listed (newest first)."""
    latest: dict[str, dict] = {}
    for s in statuses:
        ctx = str(s.get("context", ""))
        have = latest.get(ctx)
        if have is None or int(s.get("id") or 0) > int(have.get("id") or 0):
            latest[ctx] = s
    return latest


def _state(s: dict) -> str:
    return str(s.get("status") or s.get("state") or "").lower()


def _cancelled(s: dict) -> bool:
    return _state(s) == "failure" and str(s.get("description") or "").strip().lower().startswith(CANCELLED_PREFIXES)


def combine(statuses: list[dict]) -> str:
    """Gitea's combine rule over the latest status per context: any failure wins, then pending, else success.

    ``skipped`` counts as success; no statuses at all is reported as ``none`` (Gitea says ``pending`` with a zero
    count, which means "no CI reported", not "running").
    """
    states = {_state(s) for s in latest_per_context(statuses).values()}
    if not states:
        return "none"
    if states & FAILING:
        return "failure"
    if "pending" in states:
        return "pending"
    return "success"


def failing_contexts(statuses: list[dict]) -> frozenset[str]:
    return frozenset(c for c, s in latest_per_context(statuses).items() if _state(s) in FAILING)


def commit_outcome(client: GiteaClient, owner: str, repo: str, sha: str) -> CommitCI:
    """A commit's CI outcome. Cancelled Actions jobs are set aside; if nothing else failed, the commit is cancelled."""
    latest = latest_per_context(client.commit_statuses(owner, repo, sha))
    real = {c: s for c, s in latest.items() if not _cancelled(s)}
    outcome = combine(list(real.values()))
    if outcome == "none" and latest:
        return CommitCI(sha, "cancelled")
    if outcome == "success" and len(real) < len(latest):
        outcome = "cancelled"  # every failure was a cancelled job: neither a pass nor a real failure
    return CommitCI(sha, outcome, failing_contexts(list(real.values())))  # type: ignore[arg-type]


def label_ids(client: GiteaClient, owner: str, repo: str, names: list[str]) -> dict[str, int]:
    """Resolve label names to IDs once, from organisation then repository labels (a repository label wins a clash).

    Missing labels are reported, never created: people create labels.
    """
    have = {str(lbl["name"]): int(lbl["id"]) for lbl in client.org_labels(owner)}
    have |= {str(lbl["name"]): int(lbl["id"]) for lbl in client.repo_labels(owner, repo)}
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
    """Refuse to run with push, admin or merge rights: Jev comments and labels, nothing more. Returns the bot login.

    Rights that cannot be read count as a failed check, never as "no rights".
    """
    login = client.me()
    for owner, repo in sorted(repos):
        info = client.repo_info(owner, repo)
        perms = info.get("permissions")
        if not isinstance(perms, dict) or "push" not in perms or "admin" not in perms:
            raise PermissionError(f"cannot read Jev's repository permissions on {owner}/{repo}; refusing to run")
        if perms["push"] or perms["admin"]:
            raise PermissionError(
                f"Jev's account {login!r} has {'admin' if perms['admin'] else 'push'} permission on {owner}/{repo}; "
                "give it a team with code read, issues write, pulls write, actions read only"
            )
        branch = str(info["default_branch"])
        can_push, can_merge = client.branch_rights(owner, repo, branch)
        if can_push or can_merge:
            raise PermissionError(
                f"Jev's account {login!r} can {'push' if can_push else 'merge'} on {owner}/{repo}:{branch}; "
                "give it a team with code read, issues write, pulls write, actions read only"
            )
    return login


class HttpGiteaClient:
    """Token-authenticated REST client.

    Token scopes: ``read:repository``, ``write:issue``, ``read:user`` (for ``GET /user``), and
    ``read:organization`` when the ``jev/*`` labels live at organisation level.
    """

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
            return (json.loads(raw) if raw else None), headers
        except urllib.error.HTTPError as exc:
            raise GiteaError(f"{method} {path} → HTTP {exc.code}", exc.code) from exc
        except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
            raise GiteaError(f"{method} {path} → {exc}") from exc
        except ValueError as exc:  # a 200 that is not JSON: a login page from a proxy, a truncated body
            raise GiteaError(f"{method} {path} → response is not JSON: {exc}") from exc

    def _get(self, path: str, query: dict | None = None) -> Any:
        return self._request("GET", path, query=query)[0]

    def _paged(self, path: str, query: dict | None = None) -> list[dict]:
        """Every item: read until ``X-Total-Count`` is reached or a page comes back empty (the limit may be clamped)."""
        out: list[dict] = []
        page = 1
        while True:
            batch, headers = self._request("GET", path, query={**(query or {}), "limit": PAGE, "page": page})
            batch = batch or []
            out += batch
            total = str(headers.get("x-total-count") or "")
            if not batch or (total.isdigit() and len(out) >= int(total)):
                return out
            if page >= MAX_PAGES:
                raise GiteaError(f"GET {path} → paging did not end after {MAX_PAGES} pages")
            page += 1

    def me(self) -> str:
        return str(self._get("/user")["login"])

    def version(self) -> str:
        return str(self._get("/version")["version"])

    def repo_info(self, owner: str, repo: str) -> dict:
        return self._get(f"/repos/{owner}/{repo}") or {}

    def branch_rights(self, owner: str, repo: str, branch: str) -> tuple[bool, bool]:
        b = self._get(f"/repos/{owner}/{repo}/branches/{urllib.parse.quote(branch, safe='')}") or {}
        if "user_can_push" not in b or "user_can_merge" not in b:
            raise PermissionError(f"cannot read Jev's rights on {owner}/{repo}:{branch}; refusing to run")
        return bool(b["user_can_push"]), bool(b["user_can_merge"])

    def branch_commits(self, owner: str, repo: str, branch: str, limit: int) -> list[dict]:
        try:
            rows = self._get(f"/repos/{owner}/{repo}/commits", {"sha": branch, "limit": limit, "stat": "false"}) or []
        except GiteaError as exc:
            if exc.status == 404:  # the branch is not pushed yet
                return []
            raise
        return [
            {"sha": r["sha"], "created": r.get("created") or (r.get("commit") or {}).get("committer", {}).get("date")}
            for r in rows
        ]

    def commit_statuses(self, owner: str, repo: str, sha: str) -> list[dict]:
        return self._paged(f"/repos/{owner}/{repo}/commits/{sha}/statuses")

    def list_comments(self, owner: str, repo: str, issue: int) -> list[dict]:
        return self._get(f"/repos/{owner}/{repo}/issues/{issue}/comments") or []

    def create_comment(self, owner: str, repo: str, issue: int, body: str) -> int:
        return int(self._request("POST", f"/repos/{owner}/{repo}/issues/{issue}/comments", {"body": body})[0]["id"])

    def edit_comment(self, owner: str, repo: str, comment_id: int, body: str) -> None:
        self._request("PATCH", f"/repos/{owner}/{repo}/issues/comments/{comment_id}", {"body": body})

    def repo_labels(self, owner: str, repo: str) -> list[dict]:
        return self._paged(f"/repos/{owner}/{repo}/labels")

    def org_labels(self, owner: str) -> list[dict]:
        try:
            return self._paged(f"/orgs/{owner}/labels")
        except GiteaError as exc:
            if exc.status == 404:  # a user-owned repository: no organisation labels
                return []
            raise

    def add_labels(self, owner: str, repo: str, issue: int, label_ids: list[int]) -> list[int]:
        body = self._request("POST", f"/repos/{owner}/{repo}/issues/{issue}/labels", {"labels": label_ids})[0] or []
        return [int(lbl["id"]) for lbl in body]

    def remove_label(self, owner: str, repo: str, issue: int, label_id: int) -> None:
        self._request("DELETE", f"/repos/{owner}/{repo}/issues/{issue}/labels/{label_id}")

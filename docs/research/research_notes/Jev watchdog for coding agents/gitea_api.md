# Gitea REST API for a read-mostly watchdog bot (Gitea 28.x)

Scope and method: every endpoint below was checked against the Gitea source at tag **v28.2.0**
(commit `829b49c1`, 2026-10-18, the newest release tag on 2026-10-22), including the generated swagger
spec `templates/swagger/v1-swagger.generated.json` and the Go handlers and structs. Older tags
(v1.18.0 to v1.27.0, v28.0.0) were checked out to find when behaviour changed. All API paths are
relative to `https://<host>/api/v1`.

Versioning context: Gitea's tags go `v1.27.0` (2026-07-13) … `v1.27.3`, then `v28.0.0` (2026-09-29),
`v28.1.0` (2026-10-06) and `v28.2.0` (2026-10-18). There is a `v1.28.0-dev` tag but no `v1.28.0`
release, so "28.x" is the release after 1.27, with the leading "1." dropped
([git tags, go-gitea/gitea](https://github.com/go-gitea/gitea/tags);
[AlternativeTo news, Sept 2026](https://alternativeto.net/news/2026/9/gitea-drops-legacy-versioning-with-major-28-0-release-and-adds-audit-logging-bot-accounts/)).
The Go module was also renamed to `gitea.dev` (the swagger has `x-go-package: gitea.dev/modules/structs`)
([go.mod](https://github.com/go-gitea/gitea/blob/v28.2.0/go.mod)). The REST API base path is still
`/api/v1`.

Docs note: `docs.gitea.com` and `gitea.com` were blocked from this research environment (DNS failure
and proxy 403), so the hosted swagger and the docs site could not be read. Everything here comes from
source. Each instance serves its own spec at `GET /swagger.v1.json` (and `/openapi3.v1.json`), with the
UI at `GET /api/swagger`
([routers/web/web.go L303, L1779-1780](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/web/web.go#L1779)).
Use those URLs on the target instance to check the exact deployed version.

---

## 1. Commit status: combined and per-context endpoints, state values, CI state of a branch head, and Gitea Actions run endpoints

### Takeaway
To get the CI verdict for a branch head, call `GET /repos/{owner}/{repo}/commits/{branch}/status?limit=50`
with a `read:repository` token. In 28.x the combined `state` is only ever `pending`, `success` or
`failure`: `warning` and `error` both collapse to `failure`, `skipped` counts as success, and zero
statuses means `pending`. The combined state is computed over the **returned page only**, so a repo with
more contexts than the page size can get a wrong verdict. Check the `X-Total-Count` header, or page
through `/statuses`.

### Cited Findings
**Endpoints (swagger operationIds, v28.2.0)** — [v1-swagger.generated.json](https://github.com/go-gitea/gitea/blob/v28.2.0/templates/swagger/v1-swagger.generated.json); handlers in [routers/api/v1/repo/status.go](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/repo/status.go)

| Method | Path | operationId | Query params | Response |
|---|---|---|---|---|
| GET | `/repos/{owner}/{repo}/commits/{ref}/status` | `repoGetCombinedStatusByRef` | `page`, `limit` | 200 `CombinedStatus`; 400; 404 |
| GET | `/repos/{owner}/{repo}/commits/{ref}/statuses` | `repoListStatusesByRef` | `sort` ∈ {oldest, recentupdate, leastupdate, leastindex, highestindex}; `state` ∈ {pending, success, error, failure, warning}; `page`; `limit` | 200 `[]CommitStatus`; 400; 404 |
| GET | `/repos/{owner}/{repo}/statuses/{sha}` | `repoListStatuses` | same as above | 200 `[]CommitStatus` |
| POST | `/repos/{owner}/{repo}/statuses/{sha}` | `repoCreateStatus` | body `CreateStatusOption` | 201 `CommitStatus` (watchdog should NOT need this) |

- `{ref}` is "name of branch/tag/commit". The route is a path-group match (`/<ref:*>/status`), so branch
  names containing `/` work escaped or unescaped. "Mis-configured reverse proxy might decode the `%2F`…
  so we need to support both formats" — [api.go L1546-1550](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/api.go#L1546)
- `/statuses/{sha}` "only accepts commit ID" (not a branch name) — [api.go L1536](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/api.go#L1536)
- All of these sit under `reqRepoReader(unit.TypeCode)` inside the group guarded by
  `tokenRequiresScopes(auth_model.AccessTokenScopeCategoryRepository)`, so a GET needs
  `read:repository` and read access to the Code unit — [api.go L1536-1552, L1611](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/api.go#L1611)

**Exact structs** — [modules/structs/status.go](https://github.com/go-gitea/gitea/blob/v28.2.0/modules/structs/status.go#L13)
```go
type CommitStatus struct {
	ID int64 `json:"id"`
	State commitstatus.CommitStatusState `json:"status"`   // NOTE: JSON key is "status", not "state"
	TargetURL string `json:"target_url"`
	Description string `json:"description"`
	URL string `json:"url"`
	Context string `json:"context"`
	Creator *User `json:"creator"`
	Created time.Time `json:"created_at"`
	Updated time.Time `json:"updated_at"`
}
type CombinedStatus struct {
	State commitstatus.CommitStatusState `json:"state"`
	SHA string `json:"sha"`
	TotalCount int `json:"total_count"`
	Statuses []*CommitStatus `json:"statuses"`
	Repository *Repository `json:"repository"`
	CommitURL string `json:"commit_url"`
	URL string `json:"url"`
}
type CreateStatusOption struct {
	State commitstatus.CommitStatusState `json:"state"`
	TargetURL string `json:"target_url"`
	Description string `json:"description"`
	Context string `json:"context"`
}
```
- The JSON key mismatch (`status` on an individual `CommitStatus`, `state` on `CombinedStatus` and
  `CreateStatusOption`) has been there since at least v1.22.0. Parsers must read
  `statuses[].status`. — [v1.22.0 status.go](https://github.com/go-gitea/gitea/blob/v1.22.0/modules/structs/status.go); [v28.2.0 status.go](https://github.com/go-gitea/gitea/blob/v28.2.0/modules/structs/status.go#L13)

**State enum and how states combine (28.x)** — [modules/commitstatus/commit_status.go](https://github.com/go-gitea/gitea/blob/v28.2.0/modules/commitstatus/commit_status.go#L67)
- Individual states: `pending`, `success`, `error`, `failure`, `warning`, `skipped`.
- `Combine()` (verbatim comment): "failure if any of the contexts report as error or failure; failure if
  any of the contexts report as warning (Gitea specific behavior); pending if there are no statuses or
  a context is pending; success if the latest status for all contexts is success". In code, `skipped`
  counts like `success` (`case state.IsSuccess() || state.IsSkipped(): successCnt++`).
- When there are no statuses, `ToCombinedStatus` sets `State = pending`, leaves `Statuses` unset
  (JSON `null`) and `TotalCount = 0` — [services/convert/status.go L46-63](https://github.com/go-gitea/gitea/blob/v28.2.0/services/convert/status.go#L46)
- Only the **latest status per context** counts. `GetLatestCommitStatus` selects
  `max(index) … GROUP BY context_hash` — [models/git/commit_status.go L343-359](https://github.com/go-gitea/gitea/blob/v28.2.0/models/git/commit_status.go#L343)

**Version history of the combine rule** (checked by reading each tag's file):
- ≤ v1.24: a priority ordering `error(0) < failure(1) < warning(2) < pending(3) < success(4)`, so the
  combined state could be `error` or `warning`; no `skipped` state existed — [v1.24.0 commit_status.go](https://github.com/go-gitea/gitea/blob/v1.24.0/modules/structs/commit_status.go)
- v1.25: a GitHub-style `Combine()` was added along with the `skipped` state. `warning` counted as
  success then — [v1.25.0 commitstatus/commit_status.go](https://github.com/go-gitea/gitea/blob/v1.25.0/modules/commitstatus/commit_status.go)
- v1.26 through v28.2: `warning` → `failure` — [v1.26.0](https://github.com/go-gitea/gitea/blob/v1.26.0/modules/commitstatus/commit_status.go), [v28.2.0](https://github.com/go-gitea/gitea/blob/v28.2.0/modules/commitstatus/commit_status.go#L67)
- The swagger `state` filter enum on the `/statuses` endpoints still lists only the five pre-1.25
  values (no `skipped`) — [swagger](https://github.com/go-gitea/gitea/blob/v28.2.0/templates/swagger/v1-swagger.generated.json)

**Paging problem in the combined endpoint**
- `GetCombinedCommitStatusByRef` passes `utils.GetListOptions(ctx)` (default 30, max 50) into
  `GetLatestCommitStatus`, then `ToCombinedStatus` runs `CalcCommitStatus` over that page only.
  `total_count` in the body is `len(statuses)` of the page. The real number of contexts goes in the
  `X-Total-Count` header (`CountLatestCommitStatus`), and a `Link` header is set — [status.go L254-277](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/repo/status.go#L254); [convert/status.go L46-55](https://github.com/go-gitea/gitea/blob/v28.2.0/services/convert/status.go#L46)

**Reading the branch head SHA**
- `GET /repos/{owner}/{repo}/branches/{branch}` (`repoGetBranch`) returns `Branch` with `commit`
  (`PayloadCommit`: `id`, `message`, `timestamp`, `url`, …), `protected`, `enable_status_check`,
  `status_check_contexts`, `required_approvals`, `user_can_push`, `user_can_merge` and
  `effective_branch_protection_name` — [swagger Branch definition](https://github.com/go-gitea/gitea/blob/v28.2.0/templates/swagger/v1-swagger.generated.json); [modules/structs/repo_branch.go](https://github.com/go-gitea/gitea/blob/v28.2.0/modules/structs/repo_branch.go)

**How Gitea Actions shows up in commit statuses**
- Each Actions job writes a commit status with context `"<workflow display name> / <job name> (<event>)"`.
  Scoped runs get a prefix: `"<prefix>: <display> / <job> (<event>)"` — [modules/actions/workflows.go L159-165](https://github.com/go-gitea/gitea/blob/v28.2.0/modules/actions/workflows.go#L159); [services/actions/commit_status.go L158-167](https://github.com/go-gitea/gitea/blob/v28.2.0/services/actions/commit_status.go#L158)
- Mapping from job status to commit status: Success→`success`; Failure **and Cancelled**→`failure`;
  Waiting/Blocked/Pending/Running/Cancelling→`pending`; Skipped→`skipped`; anything else→`error`. The
  target URL is `<run link>/jobs/<job id>` — [services/actions/commit_status.go L166, L373-386](https://github.com/go-gitea/gitea/blob/v28.2.0/services/actions/commit_status.go#L373)

**Actions run endpoints (optional detail for diagnostics)** — [api.go L1405-1428](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/api.go#L1405), all under `reqRepoReader(unit.TypeActions)` and the repository scope category
- `GET /repos/{owner}/{repo}/actions/runs` (`getWorkflowRuns`): query `event`, `branch`, `status`
  ("requested, pending, queued, in_progress, failure, success, skipped"), `actor`, `head_sha`,
  `exclude_pull_requests`, `page`, `limit`. Returns `{total_count, workflow_runs: []ActionWorkflowRun}` — [swagger](https://github.com/go-gitea/gitea/blob/v28.2.0/templates/swagger/v1-swagger.generated.json)
- `GET /repos/{owner}/{repo}/actions/runs/{run}` (`GetWorkflowRun`) and
  `GET /repos/{owner}/{repo}/actions/runs/{run}/jobs` (`listWorkflowRunJobs`; query `status`, `page`,
  `limit`, `sort`=id, `order`=asc|desc) — [swagger](https://github.com/go-gitea/gitea/blob/v28.2.0/templates/swagger/v1-swagger.generated.json)
- Also present: `GET /repos/{owner}/{repo}/actions/runs/{run}/attempts/{attempt}` and `/attempts/{attempt}/jobs`,
  plus `GET …/runs/{run}/logs` (needs a token). Write operations (`rerun`, `cancel`, `approve`, DELETE)
  require `reqRepoWriter(unit.TypeActions)` — [api.go L1405-1425](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/api.go#L1405)
- `ActionWorkflowRun` fields include `id`, `run_number`, `run_attempt`, `status`, `conclusion`,
  `head_branch`, `head_sha`, `event`, `display_title`, `path`, `html_url`, `jobs_url`, `logs_url`,
  `started_at`, `completed_at`, `created_at`, `updated_at`, `actor`, `trigger_actor`, `pull_requests` — [swagger ActionWorkflowRun](https://github.com/go-gitea/gitea/blob/v28.2.0/templates/swagger/v1-swagger.generated.json)
- API `status` values: `queued` (waiting), `pending` (blocked), `requested` (pending),
  `in_progress` (running or cancelling), `completed`. When completed, `conclusion` ∈ {`success`,
  `cancelled`, `failure`, `skipped`} — [services/convert/convert.go L445-471](https://github.com/go-gitea/gitea/blob/v28.2.0/services/convert/convert.go#L445)

### Inferences
- Recommended call: `GET /repos/{o}/{r}/commits/{branch}/status?limit=50`. If the `X-Total-Count`
  header is greater than the number of statuses returned, read every page of
  `/commits/{sha}/statuses?sort=highestindex` (or fetch more combined pages) and combine them client-side
  with the same rule. Also pin the head SHA from the response's `sha` field, so later actions refer to
  the exact commit that was judged.
- Treat `state == "pending" && total_count == 0` as "no CI reported", not "CI running". Gitea returns
  the same `pending` in both cases.
- Because Cancelled maps to `failure`, a run cancelled by a newer push shows as failure on the old SHA.
  A watchdog should judge only the current head SHA.
- A watchdog spanning Gitea versions must branch on version: before 1.25, `error`/`warning` combined
  states appear; in 1.25 `warning` passed. Use `GET /api/v1/version` to decide.

### Gaps
- The hosted docs ([docs.gitea.com API](https://docs.gitea.com/api/) and gitea.com/api/swagger) could
  not be fetched (blocked from this environment), so I could not confirm which version the hosted docs
  show. Each instance's own `/swagger.v1.json` is authoritative for that instance.
- I did not find which PRs introduced the 1.25 and 1.26 changes to `Combine()`; only the tag-to-tag
  difference is verified.

---

## 2. Issue comments: list and create

### Takeaway
`GET /repos/{owner}/{repo}/issues/{index}/comments` does **not paginate**. It returns every plain comment,
oldest first, with optional `since`/`before` filters. `POST` with `{"body": "..."}` returns 201 `Comment`.
Both work for PRs, because a PR's index is an issue index. Reads need `read:issue`, writes need
`write:issue`. Only **read** access to the Issues or Pull Requests unit is needed to comment, unless the
issue is locked.

### Cited Findings
- Routes: `m.Combo("").Get(repo.ListIssueComments).Post(reqToken(), mustNotBeArchived, bind(api.CreateIssueCommentOption{}), repo.CreateIssueComment)`,
  inside the group guarded by `tokenRequiresScopes(auth_model.AccessTokenScopeCategoryIssue)` — [api.go L1665-1667, L1750](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/api.go#L1667)
- Swagger `issueGetComments`: path `index` (int64); query `since` (date-time, "only comments updated
  since the specified time"), `before` (date-time). **No `page`/`limit` parameters.** Response 200
  `CommentList`, 404 — [swagger](https://github.com/go-gitea/gitea/blob/v28.2.0/templates/swagger/v1-swagger.generated.json)
- Handler: builds `FindCommentsOptions{IssueID, Since, Before, Type: CommentTypeComment}` with no
  ListOptions, sets `X-Total-Count`, and returns 404 if the caller cannot read issues or PRs — [issue_comment.go L28-~120](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/repo/issue_comment.go#L28)
- `FindComments` paginates only `if opts.Page > 0` and orders `Asc("comment.created_unix").Asc("comment.id")` — [models/issues/comment.go](https://github.com/go-gitea/gitea/blob/v28.2.0/models/issues/comment.go)
- Only `CommentTypeComment` rows are returned. Label, status and review events are excluded. Use
  `GET /repos/{owner}/{repo}/issues/{index}/timeline` (`ListIssueCommentsAndTimeline`) for those — [api.go L1671](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/api.go#L1671); [issue_comment.go L124](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/repo/issue_comment.go#L124)
- Repo-wide listing `GET /repos/{owner}/{repo}/issues/comments` (`ListRepoIssueComments`) also exists — [api.go](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/api.go#L1636)
- Create body, exact struct — [modules/structs/issue_comment.go L37](https://github.com/go-gitea/gitea/blob/v28.2.0/modules/structs/issue_comment.go#L37):
  ```go
  type CreateIssueCommentOption struct {
  	// required:true
  	Body string `json:"body" binding:"Required"`
  }
  ```
- Create responses: 201 `Comment`, 403 forbidden, 404, 423 `repoArchivedError` — [swagger issueCreateComment](https://github.com/go-gitea/gitea/blob/v28.2.0/templates/swagger/v1-swagger.generated.json)
- Create permission logic: requires `CanReadIssuesOrPulls(issue.IsPull)` (otherwise 404). If
  `issue.IsLocked`, also requires `CanWriteIssuesOrPulls` or site admin (otherwise 403
  "comment_on_locked"). A blocked user gets 403 — [issue_comment.go L344-~380](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/repo/issue_comment.go#L344)
- `Comment` response fields: `id`, `body`, `user`, `html_url`, `issue_url`, `pull_request_url`,
  `created_at`, `updated_at`, `assets`, `original_author`, `original_author_id` — [swagger Comment](https://github.com/go-gitea/gitea/blob/v28.2.0/templates/swagger/v1-swagger.generated.json)
- Edit or delete your own comment: `PATCH`/`DELETE /repos/{owner}/{repo}/issues/comments/{id}` (`EditIssueCommentOption`) — [swagger](https://github.com/go-gitea/gitea/blob/v28.2.0/templates/swagger/v1-swagger.generated.json)

### Inferences
- For idempotent "one status comment per PR", list the comments, find the bot's own comment (by
  `user.login` plus a hidden marker in `body`), and `PATCH` it instead of posting again. Use `since`
  to keep polling cheap, since there is no paging.
- On very long threads the unpaginated list can be large. Prefer `since=<last seen updated_at>`.

### Gaps
- I did not measure response size or latency for issues with thousands of comments.

---

## 3. Labels: add (POST) and replace (PUT); IDs vs names; repo label lookup and creation; org labels

### Takeaway
`IssueLabelsOption.labels` takes **either** a list of integer IDs **or** a list of string names, never a
mix (mixing gives 400). Names have been accepted since **v1.22.0** (PR #30943, backported as #30958).
Org-level labels have resolved by name since **v1.23.0**. Unknown names are **silently dropped**, so
creating a missing label first is the caller's job. Both POST and PUT return 200 with the issue's
resulting full label list. Label names are not unique in the database, so "create if missing" can race
and produce duplicates.

### Cited Findings
**Endpoints** — [api.go L1672-1677](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/api.go#L1672) (issue scope category, [L1750](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/api.go#L1750))

| Method | Path | operationId | Body | Response |
|---|---|---|---|---|
| GET | `/repos/{o}/{r}/issues/{index}/labels` | `issueGetLabels` | – | 200 `[]Label` |
| POST | `/repos/{o}/{r}/issues/{index}/labels` | `issueAddLabel` | `IssueLabelsOption` | 200 `[]Label` (all labels now on the issue); 403; 404; 423 |
| PUT | `/repos/{o}/{r}/issues/{index}/labels` | `issueReplaceLabels` | `IssueLabelsOption` | 200 `[]Label`; 403; 404; 423 |
| DELETE | `/repos/{o}/{r}/issues/{index}/labels` | `issueClearLabels` | – | 204 |
| DELETE | `/repos/{o}/{r}/issues/{index}/labels/{id}` | `issueRemoveLabel` | – (`id` is int64 only, no names) | 204; 403; 404; 422; 423 |
| GET | `/repos/{o}/{r}/labels` | `issueListLabels` | query `page`, `limit` | 200 `[]Label` |
| POST | `/repos/{o}/{r}/labels` | `issueCreateLabel` | `CreateLabelOption` | 201 `Label`; 404; 422 |
| GET/PATCH/DELETE | `/repos/{o}/{r}/labels/{id}` | `issueGetLabel`/`issueEditLabel`/`issueDeleteLabel` | `EditLabelOption` | |
| GET | `/orgs/{org}/labels` | `orgListLabels` | `page`, `limit` | 200 `[]Label` |
| POST | `/orgs/{org}/labels` | `orgCreateLabel` | `CreateLabelOption` | 201 (org owners only) |

Source: [swagger](https://github.com/go-gitea/gitea/blob/v28.2.0/templates/swagger/v1-swagger.generated.json).

**Exact structs** — [modules/structs/issue_label.go](https://github.com/go-gitea/gitea/blob/v28.2.0/modules/structs/issue_label.go#L57)
```go
// IssueLabelsOption a collection of labels
type IssueLabelsOption struct {
	// Labels can be a list of integers representing label IDs
	// or a list of strings representing label names
	Labels []any `json:"labels"`
}
type CreateLabelOption struct {
	// required:true
	Name string `json:"name" binding:"Required"`
	Exclusive bool `json:"exclusive"`            // example: false
	// required:true
	Color string `json:"color" binding:"Required"` // example: #00aabb
	Description string `json:"description"`
	IsArchived bool `json:"is_archived"`
}
type Label struct {
	ID int64 `json:"id"`; Name string `json:"name"`; Exclusive bool `json:"exclusive"`
	IsArchived bool `json:"is_archived"`; Color string `json:"color"` // example: 00aabb
	Description string `json:"description"`; URL string `json:"url"`
}
```
- Swagger renders `labels` as `type: array, items: {}` (untyped), so generated clients may type it badly — [swagger IssueLabelsOption](https://github.com/go-gitea/gitea/blob/v28.2.0/templates/swagger/v1-swagger.generated.json)

**How IDs and names are resolved** — [routers/api/v1/repo/issue_label.go `prepareForReplaceOrAdd` L318-378](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/repo/issue_label.go#L318)
- Each element is checked with reflection: `reflect.Float64` → ID, `reflect.String` → name. Anything
  else → 400 "a label must be an integer or a string".
- `if len(labelIDs) > 0 && len(labelNames) > 0` → 400 "labels should be an array of strings or integers".
- Names are looked up with `GetLabelIDsInRepoByNames(repoID, names)`. When the owner is an
  organization, `GetLabelIDsInOrgByNames(ownerID, names)` is also called and both ID sets are appended.
  A name that exists at both repo and org level therefore adds both labels.
- `GetLabelIDsInRepoByNames` is a plain `WHERE repo_id = ? AND name IN (...)`, so missing names give no
  error and are skipped — [models/issues/label.go L374-382](https://github.com/go-gitea/gitea/blob/v28.2.0/models/issues/label.go#L374)
- IDs that belong to another repo or org are silently skipped when added:
  `(l.RepoID != issue.RepoID && l.OrgID != issue.Repo.OwnerID)` — [models/issues/issue_label.go L116-128](https://github.com/go-gitea/gitea/blob/v28.2.0/models/issues/issue_label.go#L116)
- Exclusive (scoped) labels: adding `scope/x` removes any other label on the issue with the same
  exclusive scope — [models/issues/issue_label.go L64-71](https://github.com/go-gitea/gitea/blob/v28.2.0/models/issues/issue_label.go#L64)
- Permission: both add and replace require `ctx.Repo.Permission.CanWriteIssuesOrPulls(issue.IsPull)`,
  which is **write** on the Issues unit for issues, or on the Pull Requests unit for PRs. Without it the
  call returns 403 "write permission is required" — [issue_label.go L329-332](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/repo/issue_label.go#L329); [models/perm/access/repo_permission.go L159-164](https://github.com/go-gitea/gitea/blob/v28.2.0/models/perm/access/repo_permission.go#L159)

**Version history**
- v1.18.0 to v1.21.0: `Labels []int64 \`json:"labels"\`` ("list of label IDs"), so IDs only — [v1.21.0 issue_label.go](https://github.com/go-gitea/gitea/blob/v1.21.0/modules/structs/issue_label.go)
- v1.22.0: `Labels []any` with names accepted. The commit is `f806bbb8` "Support using label names when
  changing issue labels (#30943) (#30958)", dated 2024-05-13 — [v1.22.0 issue_label.go](https://github.com/go-gitea/gitea/blob/v1.22.0/modules/structs/issue_label.go); [PR #30943](https://github.com/go-gitea/gitea/pull/30943); [backport #30958](https://github.com/go-gitea/gitea/pull/30958)
- In v1.22.0, names resolved only against **repo** labels. The org-label lookup by name
  (`GetLabelIDsInOrgByNames`) first appears in v1.23.0 and is still present in v28.2.0 — [v1.22.0 handler](https://github.com/go-gitea/gitea/blob/v1.22.0/routers/api/v1/repo/issue_label.go); [v1.23.0 handler](https://github.com/go-gitea/gitea/blob/v1.23.0/routers/api/v1/repo/issue_label.go)

**Looking up and creating repo labels**
- `GET /repos/{o}/{r}/labels` has **no name filter**, only `page`, `limit` (and an undocumented `sort`
  form value). It returns **repo labels only**: `GetLabelsByRepoID` + `ToLabelList(labels, repo, nil)`.
  Org labels come from `/orgs/{org}/labels`. `X-Total-Count` is set — [routers/api/v1/repo/label.go ListLabels](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/repo/label.go)
- Creating a repo label: `POST /repos/{o}/{r}/labels` needs `reqToken()` and
  `reqRepoWriter(unit.TypeIssues, unit.TypePullRequests)` (write on either unit), plus `write:issue`.
  The color is normalized (`#00aabb` or `00aabb`); an invalid color gives 422 — [api.go L1732-1734](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/api.go#L1732); [label.go CreateLabel](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/repo/label.go); [services/context/api.go L334-336](https://github.com/go-gitea/gitea/blob/v28.2.0/services/context/api.go#L334)
- `NewLabel` is a plain `db.Insert`. The `Label` model has no unique index on `Name` (only `RepoID` and
  `OrgID` are indexed), so a duplicate name in the same repo is accepted — [models/issues/label.go](https://github.com/go-gitea/gitea/blob/v28.2.0/models/issues/label.go)
- Org labels: `GET /orgs/{org}/labels` is open to any org-visible caller. `POST`/`PATCH`/`DELETE` need
  `reqOrgOwnership()` (org owner). This group is guarded by the **organization** scope category, so
  creating an org label needs `write:organization` — [api.go L1815-1821, L1843](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/api.go#L1815)

### Inferences
- Robust watchdog labelling: (1) at start-up, page through `GET /repos/{o}/{r}/labels?limit=50`
  (and `/orgs/{org}/labels` for org repos), build a name→ID map, and create any missing repo label
  once. Have a person or an admin job pre-create the labels if you don't want the bot to hold
  label-creation rights. (2) Add labels **by ID** with `POST …/issues/{index}/labels {"labels":[id]}`.
  This avoids both the silent drop of unknown names and the double-add when a repo label and an org
  label share a name. (3) Check that the returned list contains the expected IDs.
- Use POST (add) rather than PUT (replace). PUT would remove labels set by people or other agents.
- Creating repo labels needs only write on the Issues or Pull Requests unit, not admin.

### Gaps
- The PR #30943 page itself could not be opened (GitHub search API blocked here). The PR number and date
  come from the commit subject in the v1.22.0 history.
- I did not establish which PR added org-label name lookup in 1.23.

---

## 4. Token scopes for a comment-and-label-only bot, and how to deny push, approve and merge

### Takeaway
Use scopes `read:repository,write:issue` (write implies read, so `read:issue` is not needed). Add
`read:organization` only if org labels must be listed. Scopes cap what a token can do. The account's
repo permission is a separate gate, and the one that actually denies push, merge and official approval.
Give the bot account **read** on Code, **write** on Issues and Pull Requests (only through an org team's
per-unit `units_map`; a plain collaborator `write` grants Code write too), and turn on branch protection
with push, merge and approvals allowlists that leave the bot out. In 28.x the account can be a dedicated
**Bot** user type, which cannot have a password or be site admin.

### Cited Findings
**Scope strings** — [models/auth/access_token_scope.go L56-84](https://github.com/go-gitea/gitea/blob/v28.2.0/models/auth/access_token_scope.go#L56)
`all`, `public-only`, `read:activitypub`, `write:activitypub`, `read:admin`, `write:admin`, `read:misc`,
`write:misc`, `read:notification`, `write:notification`, `read:organization`, `write:organization`,
`read:package`, `write:package`, `read:issue`, `write:issue`, `read:repository`, `write:repository`,
`read:user`, `write:user`.
- Each write bitmap includes the matching read bit, e.g.
  `accessTokenScopeWriteIssueBits = 1<<iota | accessTokenScopeReadIssueBits` — [L88-130](https://github.com/go-gitea/gitea/blob/v28.2.0/models/auth/access_token_scope.go#L88)
- How the required level is chosen: `tokenRequiresScopes` treats `POST`, `PUT`, `PATCH` and `DELETE` as
  Write and everything else as Read. A failure gives 403 "token does not have at least one of required
  scope(s)…". `public-only` limits the token to public resources — [api.go L328-372](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/api.go#L328)
- Route-group categories: `/repos/{o}/{r}` code, statuses, commits, branches, actions → **repository**
  ([L1611](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/api.go#L1611)); `/repos/{o}/{r}/issues…`
  and `/repos/{o}/{r}/labels`, milestones → **issue** ([L1750](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/api.go#L1750));
  `/orgs/{org}…` including labels → **organization** ([L1843](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/api.go#L1843)).

| Watchdog operation | Token scope | Repo permission (unit) |
|---|---|---|
| GET commit status / statuses / branch / actions runs | `read:repository` | read Code (Actions read for runs) |
| GET issue comments, issue labels, repo labels | `read:issue` (implied by `write:issue`) | read Issues / Pull Requests |
| POST comment | `write:issue` | **read** Issues/PRs (write if the issue is locked) |
| POST/PUT issue labels | `write:issue` | **write** Issues (issue) or Pull Requests (PR) |
| POST repo label | `write:issue` | write Issues **or** Pull Requests |
| GET org labels | `read:organization` | org visible |

Sources: [api.go](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/api.go), [issue_comment.go](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/repo/issue_comment.go#L344), [issue_label.go](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/repo/issue_label.go#L329).

- Creating the token: `POST /users/{username}/tokens` with body
  `CreateAccessTokenOption {name (required), scopes []string}`, e.g.
  `{"name":"watchdog","scopes":["read:repository","write:issue"]}` — [swagger CreateAccessTokenOption](https://github.com/go-gitea/gitea/blob/v28.2.0/templates/swagger/v1-swagger.generated.json)
- Git over HTTP with a token is also scope-checked: `context.CheckRepoScopedToken(ctx, repo, GetScopeLevelFromAccessMode(accessMode))`
  requires `write:repository` to push. A token without it cannot push over HTTPS even if the account
  could — [routers/web/repo/githttp.go L162](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/web/repo/githttp.go#L162); [services/context/permission.go L121-123](https://github.com/go-gitea/gitea/blob/v28.2.0/services/context/permission.go#L121)

**Repo permission levels**
- Collaborator: `PUT /repos/{o}/{r}/collaborators/{collaborator}` with
  `AddCollaboratorOption {permission: "read"|"write"|"admin"}`. The level applies to the whole repo, not
  per unit. `GET …/collaborators/{collaborator}/permission` returns
  `{permission, role_name, user}` — [modules/structs/repo_collaborator.go L32-45](https://github.com/go-gitea/gitea/blob/v28.2.0/modules/structs/repo_collaborator.go#L32); [swagger AddCollaboratorOption](https://github.com/go-gitea/gitea/blob/v28.2.0/templates/swagger/v1-swagger.generated.json)
- Per-unit permissions through an org team: `CreateTeamOption.units_map`, for example
  `{"repo.code":"read","repo.issues":"write","repo.pulls":"write","repo.actions":"read", …}` (values
  none/read/write/admin/owner) — [modules/structs/org_team.go CreateTeamOption](https://github.com/go-gitea/gitea/blob/v28.2.0/modules/structs/org_team.go)

**What actually gates push, merge and approval (source)**
- Merge: `(p.CanWrite(unit.TypeCode) && pb == nil) || (pb != nil && IsUserMergeWhitelisted(...))`.
  When the merge whitelist is disabled, `IsUserMergeWhitelisted` falls back to `CanWrite(unit.TypeCode)` — [services/pull/merge.go L676-691](https://github.com/go-gitea/gitea/blob/v28.2.0/services/pull/merge.go#L676); [models/git/protected_branch.go L181-201](https://github.com/go-gitea/gitea/blob/v28.2.0/models/git/protected_branch.go#L181)
- Push to a protected branch: `CanUserPush`. If `!CanPush` then false. If the whitelist is disabled,
  `CanWrite(unit.TypeCode)`. Otherwise the user must be in `WhitelistUserIDs`/`WhitelistTeamIDs` — [protected_branch.go L128-150](https://github.com/go-gitea/gitea/blob/v28.2.0/models/git/protected_branch.go#L128)
- Official approval (counts toward `required_approvals`): when there is no protection rule, write access
  to Code. When there is a rule without an approvals whitelist, "Anyone with write access is considered
  official reviewer". With the whitelist, the user must be in `ApprovalsWhitelistUserIDs`/`TeamIDs` — [protected_branch.go L227-251](https://github.com/go-gitea/gitea/blob/v28.2.0/models/git/protected_branch.go#L227); [models/issues/review.go L276-305](https://github.com/go-gitea/gitea/blob/v28.2.0/models/issues/review.go#L276)
- Branch protection body (`POST /repos/{o}/{r}/branch_protections`, `CreateBranchProtectionOption`)
  JSON fields: `rule_name`, `priority`, `enable_push`, `enable_push_whitelist`,
  `push_whitelist_usernames`, `push_whitelist_teams`, `push_whitelist_deploy_keys`, `enable_force_push`,
  `enable_force_push_allowlist`, `force_push_allowlist_usernames|teams|deploy_keys`,
  `enable_merge_whitelist`, `merge_whitelist_usernames`, `merge_whitelist_teams`,
  `enable_bypass_allowlist`, `bypass_allowlist_usernames|teams`, `enable_status_check`,
  `status_check_contexts`, `required_approvals`, `enable_approvals_whitelist`,
  `approvals_whitelist_username` (singular, sic), `approvals_whitelist_teams`,
  `block_on_rejected_reviews`, `block_on_official_review_requests`, `block_on_codeowner_reviews`,
  `block_on_outdated_branch`, `dismiss_stale_approvals`, `ignore_stale_approvals`,
  `require_signed_commits`, `protected_file_patterns`, `unprotected_file_patterns`,
  `block_admin_merge_override` — [modules/structs/repo_branch.go CreateBranchProtectionOption](https://github.com/go-gitea/gitea/blob/v28.2.0/modules/structs/repo_branch.go)
- Self-check: `GET /repos/{o}/{r}/branches/{branch}` returns `user_can_push` and `user_can_merge` for
  the **calling** user ("indicates if the current user can push to / merge to this branch") — [repo_branch.go L24-27](https://github.com/go-gitea/gitea/blob/v28.2.0/modules/structs/repo_branch.go#L24)

**Bot account type (new in 28.x)**
- `UserTypeString` is "User" | "Organization" | "Bot" (file copyright 2026). `EditUserOption.type`
  is `binding:"In(User,Organization,Bot)"` and is set by an admin through `PATCH /admin/users/{username}` — [modules/structs/user_type.go](https://github.com/go-gitea/gitea/blob/v28.2.0/modules/structs/user_type.go); [modules/structs/admin_user.go L80](https://github.com/go-gitea/gitea/blob/v28.2.0/modules/structs/admin_user.go#L80)
- A bot cannot be site admin (`ErrBotCanNotBeAdmin`) and "cannot have a password or authentication
  source" (400) — [models/user/user.go L977-978](https://github.com/go-gitea/gitea/blob/v28.2.0/models/user/user.go#L977); [routers/api/v1/admin/user.go L210-213](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/admin/user.go#L210)
- 28.0 release coverage lists "dedicated bot accounts" among the headline features — [AlternativeTo](https://alternativeto.net/news/2026/9/gitea-drops-legacy-versioning-with-major-28-0-release-and-adds-audit-logging-bot-accounts/) (secondary source; source code above is primary)

### Inferences
- Least privilege for an org-owned repo: create a Bot-type user and add it to an org team with
  `units_map` `repo.code: read`, `repo.issues: write`, `repo.pulls: write`, `repo.actions: read`, and
  everything else `none`. Issue a token with `read:repository,write:issue`. With Code at read, merge
  (`CanWrite(TypeCode)`), push (`CanUserPush`) and official approval (`HasAccessUnit(TypeCode, Write)`)
  are all denied **even without allowlists**. Turning on the push, merge and approvals whitelists on
  protected branches adds a second, independent barrier. The bot can still post a non-official
  "approve" review if it can read PRs, but that review does not count toward `required_approvals`.
- For a user-owned repo, collaborator levels are only read/write/admin. `write` would give Code write,
  so the bot would have to be a `read` collaborator. A read collaborator **can comment** but **cannot
  label** (labelling needs Issues/PRs write). Labelling with Code read-only therefore needs an org repo
  with team units. Otherwise, accept collaborator `write` and rely on branch-protection whitelists plus
  the token missing `write:repository` to block git pushes over HTTPS.
- At start-up the watchdog should call `GET …/branches/{default}` and refuse to run if
  `user_can_push` or `user_can_merge` is true. That is evidence of separated authority rather than a
  claim of it.

### Gaps
- I did not check whether `write:issue` alone lets a token submit PR reviews (`POST /repos/{o}/{r}/pulls/{index}/reviews`,
  which sits in the repository-scope group, so it likely needs `write:repository`). This was not
  confirmed line by line.
- The default unit permissions for Bot users, and any special bot-token UI rules beyond
  `AccessTokensPanel.IsBot`, were not traced.

---

## 5. Webhook signature header and HMAC algorithm

### Takeaway
`X-Gitea-Signature` is the **bare lowercase hex** HMAC-SHA256 of the raw request body, keyed with the
webhook secret, with no `sha256=` prefix. GitHub-compatible `X-Hub-Signature-256: sha256=<hex>` and
`X-Hub-Signature: sha1=<hex>` are sent as well. With no secret set, the signature headers are empty
strings.

### Cited Findings
- `addDefaultHeaders` computes `hmac.New(sha1.New, secret)` and `hmac.New(sha256.New, secret)` over
  `payloadContent`, hex-encodes both, and only does so `if len(secret) > 0` — [services/webhook/deliver.go L94-107](https://github.com/go-gitea/gitea/blob/v28.2.0/services/webhook/deliver.go#L94)
- Headers sent (verbatim): `X-Gitea-Delivery` (UUID), `X-Gitea-Event`, `X-Gitea-Event-Type`,
  `X-Gitea-Signature` (sha256 hex), `X-Gitea-Hook-Installation-Target-Type`
  (default|system|repository|organization|user), the same set as `X-Gogs-*`, `X-Hub-Signature`
  (`"sha1="+hex`), `X-Hub-Signature-256` (`"sha256="+hex`), `X-GitHub-Delivery`, `X-GitHub-Event`,
  `X-GitHub-Event-Type`, `X-GitHub-Hook-Installation-Target-Type` — [deliver.go L127-141](https://github.com/go-gitea/gitea/blob/v28.2.0/services/webhook/deliver.go#L127)
- The signed body is `t.PayloadContent` (JSON, or form-encoded for `application/x-www-form-urlencoded` hooks) — [deliver.go L44-91](https://github.com/go-gitea/gitea/blob/v28.2.0/services/webhook/deliver.go#L44)

### Inferences
- Verify with a constant-time compare of `hex(HMAC_SHA256(secret, raw_body))` against
  `X-Gitea-Signature`, and reject requests where the header is empty. Use the raw bytes, never
  re-serialized JSON.

### Gaps
- The docs page (docs.gitea.com/usage/webhooks) could not be fetched to compare its wording.

---

## 6. Rate limits and pagination defaults

### Takeaway
Pagination uses `page` (1-based) and `limit`. The default `limit` is **30** and the server caps it at
**50** (`[api] DEFAULT_PAGING_NUM` / `MAX_RESPONSE_ITEMS`). Responses carry `X-Total-Count` and a
`Link` header. I found **no built-in REST API rate limiter** in Gitea 28.2 source, so throttling, if any,
comes from a reverse proxy, and a watchdog should rate-limit itself.

### Cited Findings
- Defaults: `MaxResponseItems: 50`, `DefaultPagingNum: 30`, `DefaultGitTreesPerPage: 1000`,
  `DefaultMaxBlobSize: 10485760` — [modules/setting/api.go L16-21](https://github.com/go-gitea/gitea/blob/v28.2.0/modules/setting/api.go#L16)
- `GetListOptions` → `Page: max(ctx.FormInt("page"), 1)`, `PageSize: convert.ToCorrectPageSize(ctx.FormInt("limit"))` — [routers/api/v1/utils/page.go](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/utils/page.go)
- `ToCorrectPageSize`: `size <= 0` → `DefaultPagingNum`; `size > MaxResponseItems` → `MaxResponseItems`
  (silently clamped, no error) — [services/convert/utils.go L15-22](https://github.com/go-gitea/gitea/blob/v28.2.0/services/convert/utils.go#L15)
- The effective values are readable at runtime: `GET /settings/api` (`getGeneralAPISettings`) returns
  `GeneralAPISettings` with `max_response_items`, `default_paging_num`, `default_git_trees_per_page`,
  `default_max_blob_size`, `default_max_response_size` — [swagger](https://github.com/go-gitea/gitea/blob/v28.2.0/templates/swagger/v1-swagger.generated.json)
- `SetLinkHeader(total, pageSize)` writes an RFC 5988 `Link` header and exposes it to CORS.
  `SetTotalCountHeader` writes `X-Total-Count` — [services/context/api.go L228-236](https://github.com/go-gitea/gitea/blob/v28.2.0/services/context/api.go#L228); [services/context/base.go L74-77](https://github.com/go-gitea/gitea/blob/v28.2.0/services/context/base.go#L74)
- Exceptions: issue comments (`/issues/{index}/comments`) are not paginated (see Q2). The combined
  status's verdict covers only the page (see Q1).
- A case-insensitive search for `ratelimit|rate.limit|throttle|x-ratelimit` across `routers/`,
  `modules/setting/` and `services/context/` at v28.2.0 matched only `routers/api/v1/repo/migrate.go`
  (the word "migrate"). There is no rate-limit middleware or setting — [v28.2.0 tree](https://github.com/go-gitea/gitea/tree/v28.2.0/routers)

### Inferences
- Always send `limit=50`, loop until a page returns fewer than `limit` items (or follow the `Link`
  `rel="next"`), and cross-check against `X-Total-Count`.
- Operators can change the 30/50 defaults in `app.ini [api]`, so read the instance's
  `GET /api/v1/settings/api` before assuming the cap.

### Gaps
- I could not rule out a rate limiter in packages outside the paths searched (e.g. a 28.x
  egress or proxy layer for git network operations mentioned in release coverage, [jacar.es](https://jacar.es/?p=7623)).
  These cover outbound traffic, not inbound REST.

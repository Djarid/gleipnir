"""Seam 8 (live CI attestation fetch) — Phase 3.

Spec: `.gleipnir/plans/seam7-seam8-wiring.md`, Assemble "Phase 3 — Seam 8
live fetch + GATE" and Decision D3 ("Seam 8 mechanism": agent-unreachable
`urllib` GitHub Actions REST query; conclusion→`AttestationStatus` map).
This module is the ONLY place a genuine, externally-sourced
`gleipnir.engine.Attestation` is constructed: it queries the GitHub Actions
REST API for the `config-scan.yml` workflow's status at a given commit SHA
and maps the result to `gleipnir.engine.AttestationStatus` — never accepting
any other source of "green" (G-3.2: no self-attestation channel anywhere in
this module).

**Honest tradeoff D3(a) — STATED HERE, not only in the plan text.**
`.github/workflows/config-scan.yml` is the only CI surface today, and it
runs `bin/gleipnir-preflight config-scan` — it verifies the enforcement
roster / `opencode.jsonc` is well-scoped, NOT that this pipeline's tests
pass. Feeding its conclusion into the `Attestation` therefore attests
**config-integrity, not full artifact correctness.** GATE-on-GREEN here
means "config is well-scoped and CI ran green," not "the delivered artifact
is fully verified." A broader full-`pytest`-in-sandbox CI workflow would be
a separate, later slice.

**Honest tradeoff D3(b) — STATED HERE, not only in the plan text.** The
GitHub token (env var `GITHUB_TOKEN` — the SAME env var name
`gleipnir.broker.pm.platform` already uses for its own GitHub REST client;
reused here rather than inventing a second name for the same credential
class, per the plan's DRY principle) must be reachable by this module's
caller-edge process but NOT by any roster agent. Under the uncaged default
this rests on the SAME grant discipline as the rest of
`src/gleipnir/preflight/**` (denied to `gleipnir-code`) — cooperative-
policy, NOT structural. E-1 becomes structural only under the S-2
substrate. This module claims no stronger guarantee than that: the token is
placed only in an HTTP request header, never logged, never printed, never
included in any exception message this module raises or lets propagate.

**GitHub conclusion enum — verified, not guessed.** Checked against GitHub's
documented REST schema for a workflow run
(`docs.github.com/en/rest/actions/workflow-runs`, "Get a workflow run" /
"List workflow runs for a workflow"), cross-referenced with the community
disambiguation thread `github/docs#20643` (which quotes the same field list
GitHub's own docs give) and `actions/runner`'s ADR 0274 (step-level
outcome/conclusion, same vocabulary at the job/run level): a workflow run's
`status` field is one of `queued` / `in_progress` / `completed` (older
check-run-shaped payloads can also report `waiting` / `requested` /
`pending`); while `status != "completed"`, GitHub reports `conclusion` as
`null`. Once `status == "completed"`, `conclusion` is one of `success` /
`failure` / `neutral` / `cancelled` / `skipped` / `timed_out` /
`action_required` / `stale`. Only `success` is treated as GREEN here; every
other completed conclusion — including the ones this plan's Trace section
names by example (`failure`/`cancelled`/`timed_out`) AND the ones it does
not (`neutral`/`skipped`/`action_required`/`stale`) — maps to RED,
fail-closed: an unrecognized-but-present conclusion is never defaulted to
GREEN.

stdlib-only: `urllib.request`, `json`, `os`. No `requests`, no GitHub SDK,
no `gh` CLI shell-out (Stress-test #10).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import quote as _url_quote
from urllib.parse import urlencode as _urlencode

from gleipnir.engine import Attestation, AttestationStatus

__all__ = [
    "GITHUB_TOKEN_ENV_VAR",
    "OWNER_ENV_VAR",
    "REPO_ENV_VAR",
    "DEFAULT_WORKFLOW_FILE",
    "DEFAULT_TIMEOUT_SECONDS",
    "map_conclusion_to_status",
    "fetch_attestation",
]

# Reused, not reinvented: the SAME env var name `gleipnir.broker.pm.platform`
# already resolves its GitHub REST token from (`_TOKEN_ENV_VARS["github"]`).
GITHUB_TOKEN_ENV_VAR = "GITHUB_TOKEN"

# This module has no git-remote-parsing dependency (unlike
# `gleipnir.broker.pm.platform.RemoteInfo`, a different concern — issue
# tracking against a remote discovered by the broker process). The
# owner/repo this Seam-8 fetch targets is configuration, sourced from these
# two `GLEIPNIR_`-prefixed env vars by default, always overridable per-call
# (tests never depend on ambient env state).
OWNER_ENV_VAR = "GLEIPNIR_GITHUB_OWNER"
REPO_ENV_VAR = "GLEIPNIR_GITHUB_REPO"

DEFAULT_WORKFLOW_FILE = "config-scan.yml"
DEFAULT_TIMEOUT_SECONDS = 10.0

_GITHUB_API_BASE = "https://api.github.com"


def map_conclusion_to_status(conclusion: str | None) -> AttestationStatus:
    """Pure conclusion → `AttestationStatus` mapping. No network, no I/O —
    independently unit-testable (Stress-test #7).

    * ``"success"`` → GREEN.
    * ``None`` → PENDING (the run exists but ``status`` is
      ``"queued"``/``"in_progress"``, so GitHub reports ``conclusion: null``
      until it completes).
    * every OTHER string — including ``"failure"``/``"cancelled"``/
      ``"timed_out"`` (named in the plan's Trace) AND
      ``"neutral"``/``"skipped"``/``"action_required"``/``"stale"`` (not
      named there, but part of GitHub's documented enum — see module
      docstring) — → RED. Fail-closed: an unrecognized-but-present
      conclusion is treated as NOT green, never defaulted to green.

    Deliberately never returns ABSENT: "no matching workflow run was found
    for this SHA at all" is a fact about the QUERY (zero results), not
    about any run's ``conclusion`` field, so it is assigned by
    ``fetch_attestation`` itself — this pure function only ever sees a
    ``conclusion`` value belonging to a run that was found.
    """

    if conclusion == "success":
        return AttestationStatus.GREEN
    if conclusion is None:
        return AttestationStatus.PENDING
    return AttestationStatus.RED


def _workflow_runs_url(
    owner: str, repo: str, workflow_file: str, head_sha: str
) -> str:
    """Pure URL construction — no I/O. Queries GitHub's "list workflow runs
    for a workflow" endpoint, filtered to `head_sha`, newest first, one
    result (the caller only ever cares about the run at this exact commit).
    """

    path = (
        f"/repos/{_url_quote(owner)}/{_url_quote(repo)}/actions/workflows/"
        f"{_url_quote(workflow_file)}/runs"
    )
    query = _urlencode({"head_sha": head_sha, "per_page": "1"})
    return f"{_GITHUB_API_BASE}{path}?{query}"


def _http_get_json(url: str, token: str | None, *, timeout: float) -> Any:
    """The ONE `urllib` boundary this module calls through — mirrors
    `gleipnir.broker.pm.platform._http_request`'s "single seam" shape.
    Tests monkeypatch this attribute directly, so no live network call is
    ever exercised in the unit-test suite (Stress-test #7).

    Never logs `token`: it is placed only in the `Authorization` request
    header, never printed, never included in a raised exception's message
    (this function's own `except` clauses live in the caller,
    `_query_workflow_run_conclusion`, which never interpolates headers into
    any message either).
    """

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    return json.loads(raw.decode("utf-8"))


def _query_workflow_run_conclusion(
    head_sha: str,
    *,
    owner: str,
    repo: str,
    workflow_file: str,
    timeout: float,
) -> tuple[bool, str | None]:
    """Return ``(run_found, conclusion)``.

    ``run_found`` is ``False`` iff the query returned zero matching runs, OR
    the query itself failed for any reason (network error, timeout,
    malformed/non-JSON response, unexpected shape) — EVERY failure mode
    fails closed to "no run found", never to a fabricated conclusion.
    ``conclusion`` is only meaningful when ``run_found`` is ``True``, and is
    ``None`` while that run has not yet completed.
    """

    token = os.environ.get(GITHUB_TOKEN_ENV_VAR)
    url = _workflow_runs_url(owner, repo, workflow_file, head_sha)

    try:
        payload = _http_get_json(url, token, timeout=timeout)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        # ValueError also covers json.JSONDecodeError (a ValueError
        # subclass): a malformed response is treated the same as
        # unreachable -- fail closed, never a fabricated completed state.
        return False, None

    if not isinstance(payload, dict):
        return False, None

    runs = payload.get("workflow_runs")
    if not runs or not isinstance(runs, list):
        return False, None

    latest = runs[0]
    if not isinstance(latest, dict):
        return False, None

    conclusion = latest.get("conclusion")
    if conclusion is not None and not isinstance(conclusion, str):
        # Structurally malformed field -- fail closed rather than guess.
        return False, None

    return True, conclusion


def fetch_attestation(
    pipeline_id: str,
    head_sha: str,
    *,
    owner: str | None = None,
    repo: str | None = None,
    workflow_file: str = DEFAULT_WORKFLOW_FILE,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> Attestation:
    """Query GitHub Actions for `config-scan.yml`'s status at `head_sha`
    and construct the `Attestation` engine's `attempt_gate` consumes.

    One job (SRP, plan Design Principles): query GitHub Actions status for
    `head_sha`, map conclusion → `AttestationStatus`, construct the
    `Attestation`. Does NOT call `attempt_gate` itself (that stays the
    advance entrypoint's GIT-branch responsibility — see
    `src/gleipnir/preflight/advance.py`) and does NOT persist any state.

    `pipeline_id` is echoed verbatim into the returned `Attestation` — this
    function never asserts that `pipeline_id` matches anything; the
    pipeline_id↔SHA correlation check (Stress-test #6) is `Engine.
    attempt_gate`'s job (`engine/__init__.py` L490–496, unchanged), not
    this module's.

    `owner`/`repo` default to the `GLEIPNIR_GITHUB_OWNER`/
    `GLEIPNIR_GITHUB_REPO` env vars (never required to be set for a test —
    every test injects them explicitly). If neither is resolvable, this
    fails closed to ABSENT rather than guessing a repo to query.
    """

    resolved_owner = owner if owner is not None else os.environ.get(OWNER_ENV_VAR, "")
    resolved_repo = repo if repo is not None else os.environ.get(REPO_ENV_VAR, "")

    if not resolved_owner or not resolved_repo:
        return Attestation(pipeline_id=pipeline_id, status=AttestationStatus.ABSENT)

    run_found, conclusion = _query_workflow_run_conclusion(
        head_sha,
        owner=resolved_owner,
        repo=resolved_repo,
        workflow_file=workflow_file,
        timeout=timeout,
    )

    if not run_found:
        return Attestation(pipeline_id=pipeline_id, status=AttestationStatus.ABSENT)

    return Attestation(
        pipeline_id=pipeline_id, status=map_conclusion_to_status(conclusion)
    )

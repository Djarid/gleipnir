# Plan: Coverage + correctness on `broker/pm/platform.py` (60% → ≥85%, plus a GHE auth-header fix)

**Stage:** plan (ATLAS Architect/Trace). **Author:** gleipnir-plan.
**Scope (REVISED after spec-review + operator convergence):** this is no longer
a test-only plan. Spec-review found a real production bug in `_http_request`
(auth-header selection keys off a URL substring, not the platform), and the
operator converged (via the orchestrator) on **fix the bug AND cover it in this
same plan** — turning this into a **coverage + correctness** change. The plan now
edits BOTH `src/gleipnir/broker/pm/platform.py` (the fix) and
`tests/test_broker_pm_platform.py` (coverage + fix characterization).
**Target module:** `src/gleipnir/broker/pm/platform.py` (271 lines, stdlib-only
GitHub/GitLab REST client + remote/token parsing) — **now CHANGED** (see D7-D9).
**Test file (existing, extend):** `tests/test_broker_pm_platform.py` (210 lines).
**Spec/arbiter:** the tests this plan specifies ARE the arbiter (Axiom 1).
**Sibling precedent:** `.gleipnir/plans/broker-pm-coverage-gap.md` and
`.gleipnir/plans/broker-git-coverage-gap.md` (the two prior broker
coverage-gap plans; their test files are the convention exemplars).

---

## Decisions (index)

| # | Decision | Chosen | Rejected | Rationale |
|---|---|---|---|---|
| D1 | Where do the new tests live? | **Extend** `tests/test_broker_pm_platform.py` | New file `tests/test_broker_pm_platform_coverage.py` | Same module's tests; the file is already in `[profile.broker].test` (profiles.toml:60, verified). A new file would need a Tier-3 operator-only profiles.toml amendment for zero benefit. Extending needs NO profiles.toml/conftest change — a real advantage over both prior broker coverage plans, which each required the operator to add their new file to the explicit list. |
| D2 | Mock boundary for the `issue_*` verb tests | Monkeypatch **`platform._http_request`** (reuse/extend the existing `_RequestRecorder`, platform.py test at line 152) | Monkeypatch `urllib` for the verb tests too | The verb tests care about URL/method/payload construction, not transport. `_RequestRecorder` already captures `method/url/token/json_body`. Mirrors the established pattern in this very file and the sibling `_Recorder` in `test_broker_pm_mcp_server.py`. |
| D3 | How to test `_http_request` itself (the real network seam, lines 148-162) | Monkeypatch **`platform.urllib.request.urlopen`** to return a fake context-manager response; assert on the constructed `urllib.request.Request` (headers/method/data) captured by a fake `Request` OR on urlopen call args | Live network; `responses`/`httpretty` third-party libs; leaving 148-162 uncovered | Must stay stdlib-only + no-live-network (test_broker_stdlib_only.py boundary; suite discipline). Patching `urllib.request.urlopen` at the module attribute is the stdlib-native seam. Header assertions require capturing the `Request` object — patch `urllib.request.Request` with a passthrough recorder, or read `request.headers`/`request.get_header` off the object handed to the fake `urlopen`. |
| D4 | Any production-code change? | **YES — one bug fix** (see D7-D9). Superseded by spec-review; the original plan asserted "no change" but spec-review found a real bug and the operator converged on fixing it here. | Test-only plan (original stance, now rejected); silently fixing without a Decision row | Spec-review found the GHE auth-header bug (D7); operator converged on **fix + cover in this plan**. The fix is the ONLY source change (D8); everything else stays test-only. |
| D5 | `urllib.request.Request` header-key normalization caveat | Assert headers case-insensitively (via `request.get_header("Authorization")` / `.has_header(...)`) OR against the dict passed in, NOT via exact `request.headers` dict-key match | Asserting `request.headers["Authorization"]` by exact case | `urllib.request.Request.header_items()` capitalizes header keys (`Authorization`→`Authorization`, but `PRIVATE-TOKEN`→`Private-token`). If tests capture the fake `urlopen`'s `Request` arg, use `.get_header("Private-token")` / `.get_header("Authorization")` (case-insensitive) to avoid a brittle false failure. This is a test-correctness decision, not a source bug. |
| D6 | Coverage target & measurement | ≥85% line **and** branch on platform.py; measured under the **broker profile** | Line-only; whole-tree cov | Delegation sets ≥85% line+branch. profiles.toml `[profile.broker].coverage` already passes `--cov=src/gleipnir/broker --cov-branch`. The prior 60% figure was measured under this same broker profile this session. |
| D7 | **The bug (spec-review finding, operator-converged to fix).** `_http_request` selects the auth header with `if "github" in url:` (platform.py:150) — a case-sensitive URL substring check. | **Fix it in this plan** (correctness + coverage) | Characterize the buggy behavior only; defer the fix to a separate plan | Every other function in the module keys off `remote.platform` (host-based `_detect_platform`). A GitHub Enterprise custom domain lacking the literal `github` substring (e.g. `git.mycorp.com`) is detected as `platform=="github"` everywhere else and routed to the `/api/v3` GHE base (line 185), but `_http_request` then sends `PRIVATE-TOKEN` instead of `Authorization: Bearer`, breaking GHE-custom-domain auth. Operator converged (via orchestrator) on **fix AND cover here**. |
| D8 | **Fix mechanism.** How `_http_request` selects the auth header. | **(a) Add a required `platform: str` keyword-only parameter** to `_http_request`; select `Authorization: Bearer` when `platform == "github"`, else `PRIVATE-TOKEN`. All 4 call sites (`issue_create/update/comment/close`) pass `platform=remote.platform` (`remote` is in scope in all four — verified). | **(b) a `use_bearer: bool` flag**; **(c) keep URL substring but make it host-aware** | (a) is consistent with the rest of the module (which already branches on `remote.platform`), reads self-documenting at the call site, and removes the fragile string check entirely. (b) pushes the github/gitlab knowledge back to every caller as an opaque boolean — less clear, same edit surface. (c) still couples transport to URL spelling. Make the param **required** (keyword-only, no default) and update ALL 4 call sites, so no caller can silently fall back to the old ambiguity. |
| D9 | **Existing-test-double signature impact of D8.** `_http_request` is a monkeypatched seam: existing tests set `platform._http_request` to fakes with a fixed signature (`_RequestRecorder.__call__(self, method, url, *, token=None, json_body=None, timeout=10.0)`, test line 159; and the `_network_forbidden(*args, **kwargs)` fake, line 133). | **Update `_RequestRecorder.__call__` to accept `platform=None`** (keyword-only) and record it; the `*args, **kwargs` fakes already tolerate the new kwarg. Update any existing happy-path assertions only if they assert on the exact call kwargs. | Leave the recorder signature unchanged | Adding a required kwarg to the real `_http_request` means every call site now passes `platform=...`; the fake standing in for it MUST accept that kwarg or the already-passing github/gitlab `issue_create` happy-path tests break with a `TypeError`. `_network_forbidden(*args, **kwargs)` is already tolerant. This is the single most likely regression from the fix — called out explicitly so `gleipnir-code` updates the double's signature in the same change. |

---

## Architect

**Problem (one sentence).** `src/gleipnir/broker/pm/platform.py` sits at 60%
line coverage with an entire real-network seam (`_http_request`) and three of
the four `issue_*` verbs unexercised, AND `_http_request` carries a real
auth-header bug (selects the header by URL substring, not platform — D7); raise
coverage to ≥85% line+branch by extending the existing test file with no live
network, and fix the bug so a GitHub Enterprise custom domain gets the correct
`Authorization: Bearer` header.

**User.** The Gleipnir maintainer/operator running `bin/gleipnir-sandbox test`
(broker profile) and the `quality-reviewer` gate that reads the coverage number
as evidence the PM REST client is characterized.

**Measurable success criteria.**
1. `platform.py` line coverage ≥85% and branch coverage ≥85% under the broker
   profile (`--cov=src/gleipnir/broker --cov-branch`).
2. Every miss range from the delegation is closed: 61, 89→100, 92-94, 97→100,
   120, 148-162, 185, 222, 232-239, 244-255, 260-271 (all verified against
   source this session — see Trace).
3. All existing tests in `test_broker_pm_platform.py` still pass unchanged.
4. No live network is opened by the suite; `test_broker_stdlib_only.py` still
   passes (platform.py stays stdlib-only-importable — the fix adds no import).
5. **The GHE auth-header bug is fixed (D7/D8):** a custom-domain GHE
   `RemoteInfo` (`platform=="github"`, host lacking the `github` substring)
   sends `Authorization: Bearer <token>`, NOT `PRIVATE-TOKEN`, and a test proves
   the CORRECTED behavior end-to-end through `issue_* → _http_request` (mocked
   at `urllib`, so the real header-selection logic runs).
6. The ONLY source change is the `_http_request` auth-header fix + the 4 call
   sites passing `platform=remote.platform` (D8). No other `src/**` change.
7. No `profiles.toml` / `conftest.py` change required (verified: file already
   collected).

**Constraints.**
- **Stdlib-only test discipline.** No third-party HTTP-mock libs; monkeypatch
  the stdlib `urllib.request.urlopen` attribute (D3). Matches the existing
  suite and the `test_broker_stdlib_only.py` boundary.
- **No-live-network.** Mirror the existing `_network_forbidden` fake
  (platform.py test line 133) and `_RequestRecorder` (line 152): every path
  either monkeypatches `_http_request` or `urllib.request.urlopen`.
- **Both platform branches.** For `_api_base`, `_issues_endpoint`, and all four
  `issue_*` verbs, exercise BOTH github and gitlab arms (that's where the
  uncovered branches concentrate).
- **Tier-0 authorship only.** This plan is the only artifact I write. The
  implementing agent (`gleipnir-code`, test stage) writes the test file.

---

## Trace

### Artifacts and where they live (source of truth)

| Artifact | Path | Status |
|---|---|---|
| Target module | `src/gleipnir/broker/pm/platform.py` | exists (read in full; source of truth for line numbers) — **CHANGED by this plan:** the `_http_request` auth-header fix + 4 call sites pass `platform=` (D7-D9). This is the plan's only `src/**` edit. |
| Test file (to extend) | `tests/test_broker_pm_platform.py` | exists, 210 lines; add classes at end |
| Convention exemplars | `tests/test_broker_pm_mcp_server.py`, `tests/test_broker_git_mcp_server.py` | exist (mocking/recorder patterns) |
| stdlib-only boundary | `tests/test_broker_stdlib_only.py` | exists (must keep passing) |
| Profile wiring | `.gleipnir/sandbox/profiles.toml` `[profile.broker].test` | exists, line 60 already lists the test file — **NO change needed** |

### Gap → source → test mapping (every line verified against actual source)

| Miss range | Source construct (verified) | Test to add |
|---|---|---|
| **61** | `_split_owner_repo`: `if not parts: return "", ""` — reached only when `path` is TRUTHY but splits to zero parts | `parse_remote_url("https://github.com/.git")` — `_HTTPS_RE` matches with `path==".git"` → `.git` stripped → `""` → `parts==[]` → `return "", ""`. (This is the ONLY correct line-61 example; the `"https://github.com/"` URL does NOT reach line 61 — see the 89→100 row.) |
| **92-94** | `parse_remote_url` `_SSH_PROTO_RE` true-branch body (`match=`, `if match:`, assign host/path). NB: line 91, the `elif url.startswith("ssh://"):` check, is already covered whenever control reaches it — only 92-94 (the matched body) are missed. | `parse_remote_url("ssh://git@gitlab.com/owner/repo.git")` → host `gitlab.com`, owner `owner`, repo `repo`, platform `gitlab`. Add a port variant `ssh://git@host:22/owner/repo.git` to exercise `(?::\d+)?`. |
| **89→100** (branch-not-taken) | https prefix but `_HTTPS_RE` does NOT match → `if match:` (line 89) false → skip 90, fall to line 100 with empty host/path | `parse_remote_url("https://github.com/")` — `_HTTPS_RE` requires `(.+)$` after the slash, so a trailing-slash-only URL FAILS the regex entirely → host/path stay `""` → line 100 `else ("", "")` → owner/repo `""`, platform `gitlab` (`_detect_platform("")`, E2). Also `parse_remote_url("https://")`. |
| **97→100** (branch-not-taken) | else-arm `_SSH_SCP_RE` does NOT match → fall to 100 | `parse_remote_url("garbage-no-colon-no-slash")` → no regex matches → host/path `""` → owner/repo `""`. (Also drives the `else ("", "")` on line 100.) |
| **120** | `get_token`: `if not env_var: return None` (unknown platform) | `get_token("bitbucket")` → `None`; `has_token("bitbucket")` → `False`. |
| **148-162** | `_http_request` entire body | New `TestHttpRequest` class — see worked design below. |
| **185** | `_api_base`: `return f"https://{remote.host}/api/v3"` (github, host≠github.com) | Build `RemoteInfo(host="ghe.corp.example", owner="o", repo="r", platform="github")`, assert `_issues_endpoint(...)` starts with `https://ghe.corp.example/api/v3/repos/`. |
| **150 (the BUG, D7-D9)** | `_http_request` auth-header selection. **Before fix:** `if "github" in url:` (URL substring). **After fix:** select by the new `platform` param — `Authorization: Bearer` when `platform == "github"`, else `PRIVATE-TOKEN`. | **Fix + characterization test:** drive a custom-domain GHE `RemoteInfo(host="ghe.corp.example", owner="o", repo="r", platform="github")` with `GITHUB_TOKEN` set through `issue_create` → `_http_request`, **mocking at `urllib` (NOT at `_http_request`)** so the real header-selection runs. Assert the sent `Request` has `Authorization: Bearer <token>` and NO `Private-token` header. This asserts the CORRECTED behavior (operator chose to fix, not characterize the bug). URL is `https://ghe.corp.example/api/v3/...` — contains no `github` substring, so pre-fix this WOULD have (wrongly) sent PRIVATE-TOKEN; post-fix it follows `platform`. |
| **222** | `issue_create` gitlab body: `payload["description"] = body` | gitlab remote + `body="desc"` → recorded `json_body["description"] == "desc"` and no `"body"` key. |
| **232-239** | `issue_update`: no-token error + PATCH(github)/PUT(gitlab) branch | no-token structured error; github happy → method `PATCH`, url `.../issues/<id>`, fields pass through; gitlab happy → method `PUT`. |
| **244-255** | `issue_comment`: no-token + `/comments`(github) vs `/notes`(gitlab) | no-token error; github → url ends `/<id>/comments`, `json_body=={"body":...}`; gitlab → url ends `/<id>/notes`. |
| **260-271** | `issue_close`: no-token + PATCH `{state:closed}`(github) vs PUT `{state_event:close}`(gitlab) | no-token error; github → method `PATCH`, `json_body=={"state":"closed"}`; gitlab → method `PUT`, `json_body=={"state_event":"close"}`. |

### `_http_request` worked design (D3 — the one genuinely new seam)

Monkeypatch at the module attribute `platform.urllib.request.urlopen`. The
fake returns a context-manager whose `.read()` yields controllable bytes.
Capture the `Request` object handed to `urlopen` to assert headers/method/data.

```python
class _FakeResponse:
    def __init__(self, raw: bytes):
        self._raw = raw
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self): return self._raw

class _UrlopenRecorder:
    def __init__(self, raw: bytes = b""):
        self.raw = raw
        self.request = None  # the urllib.request.Request passed in
        self.timeout = None
    def __call__(self, request, timeout=None):
        self.request = request
        self.timeout = timeout
        return _FakeResponse(self.raw)
```

Install with `monkeypatch.setattr(platform.urllib.request, "urlopen", rec)`.
**Signature note (D8):** `_http_request` now takes a required keyword-only
`platform: str`. All `TestHttpRequest` cases call
`platform._http_request(method, url, token=..., platform="github"|"gitlab", json_body=...)`
explicitly and assert the header follows the **`platform` arg, not the URL**.
Assert on `rec.request` (a real `urllib.request.Request`):
- method: `rec.request.get_method() == "POST"`.
- url: `rec.request.full_url` (or `.get_full_url()`).
- headers: use **case-insensitive** getters per D5 —
  `rec.request.get_header("Authorization")`, `rec.request.get_header("Private-token")`
  (note: `urllib` capitalizes to `Private-token`), `rec.request.get_header("Content-type")`.
- data: `rec.request.data` is the JSON-encoded bytes when `json_body` given.

Cases (all in one `TestHttpRequest` class), each passing `platform=` explicitly:
1. **platform="github" (github.com URL) + token** → `get_header("Authorization") == "Bearer <token>"`,
   `get_header("Private-token") is None`.
2. **platform="gitlab" (gitlab.com URL) + token** → `get_header("Private-token") == "<token>"`,
   `get_header("Authorization") is None`.
3. **no token** (any platform) → neither auth header set; `Content-type`/`Accept` still present.
4. **json_body given** → `rec.request.data == json.dumps(body).encode("utf-8")`
   and `get_header("Content-type") == "application/json"`.
5. **empty response body** (`raw=b""`) → `_http_request(...) == {}` (line 161).
6. **non-empty body** (`raw=b'{"number":1}'`) → returns `{"number": 1}` (line 162).
7. **no json_body** → `rec.request.data is None` (the `else None` on line 155).
8. **THE FIX (D7):** `platform="github"` with a URL whose host lacks the
   `github` substring (`https://ghe.corp.example/api/v3/...`) + token →
   `get_header("Authorization") == "Bearer <token>"`, `get_header("Private-token") is None`.
   Pre-fix (URL-substring logic) this would have sent PRIVATE-TOKEN; post-fix it
   follows `platform`. This is the direct-seam proof; the full-path proof lives
   in the 150-row characterization test above.

### Integrations map

- `platform.get_token` reads `os.environ` → tests set/clear `GITHUB_TOKEN` /
  `GITLAB_TOKEN` via `monkeypatch.setenv/delenv` (existing pattern, lines
  100-120 of the test file). Reuse `FAKE_GITHUB_TOKEN` / `FAKE_GITLAB_TOKEN`.
- `issue_*` verbs → `_http_request(..., platform=remote.platform, ...)` (D8;
  mocked via `_RequestRecorder`, D2) → assert URL/method/token/json_body AND the
  new `platform` kwarg is passed. `_RequestRecorder.__call__` gains a
  `platform=None` kwarg (D9) so it accepts the new arg without a `TypeError`.
- `_http_request` → `urllib.request.urlopen` (mocked via `_UrlopenRecorder`, D3);
  header now selected by the `platform` param (D8).
- **Fix blast radius (change 3, re-verified against source):** the 4 call sites
  (`issue_create` L224, `issue_update` L238, `issue_comment` L254, `issue_close`
  L270) all call `_http_request` with keyword args and all have `remote` in
  scope → each adds `platform=remote.platform`. `_no_token_error`, `_api_base`,
  `_project_path`, `_issues_endpoint`, `parse_remote_url`, `get_token` are
  untouched by the fix. The github/gitlab `issue_create` happy-path tests
  (existing, lines 166-210) still pass PROVIDED `_RequestRecorder` accepts the
  new kwarg (D9) — that is the only existing-test impact.
- No `mcp` import, no subprocess, no filesystem writes; the fix adds no import.

### Edge cases

- **E1 — line 100 `else ("", "")` vs line 61 `return "", ""`.** Two distinct
  empty-path mechanisms: line 100's `else` fires when `path` is falsy (no regex
  matched, e.g. `"https://"` / garbage); line 61 fires when `path` is truthy but
  splits to zero parts (e.g. `"https://github.com/"`). Design BOTH (see mapping)
  so neither branch is left half-covered.
- **E2 — `_detect_platform("")`** returns `"gitlab"` (no "github" substring).
  The garbage/empty-host tests will therefore report `platform=="gitlab"`; assert
  that explicitly so the test documents the fall-through, not an accident.
- **E3 — header key casing (D5).** `PRIVATE-TOKEN` becomes `Private-token` via
  `urllib`'s `Request`. Case-insensitive getters avoid a brittle false failure
  that could be misread as a source bug.
- **E4 — `"github" in url` substring test (line 150).** For case 2 the non-github
  URL must genuinely lack the substring `github` (use `https://gitlab.com/...`,
  not `https://github-enterprise.example` which *contains* `github`). Choose the
  fixture URLs deliberately.
- **E5 — GHE `_api_base` (line 185) requires host≠`github.com` AND
  platform=="github".** A parsed `github-enterprise` host would be
  `_detect_platform`→`github` only if the host string contains "github"; build
  the `RemoteInfo` directly rather than via `parse_remote_url` to pin the exact
  host, avoiding coupling to platform-detection heuristics. The GHE fix test
  (D7) uses `host="ghe.corp.example"` (no `github` substring) precisely so the
  URL-substring bug and the platform-based fix DIVERGE — a github.com host would
  not distinguish them.
- **E7 — the fix must not regress the github.com / gitlab.com happy paths.**
  For a github.com URL the URL-substring check and the platform check AGREE
  (`"github" in url` is true AND `platform=="github"`); likewise gitlab.com
  disagrees on neither. So the existing happy-path assertions on header content
  remain correct after the fix — the ONLY behavior change is for the divergent
  GHE-custom-domain case (E5). Verified by reading the 4 call sites and the two
  existing happy-path tests.
- **E8 — required-kwarg TypeError trap (D9).** Because `platform` is a REQUIRED
  keyword-only param on the real `_http_request`, any monkeypatched double that
  does not accept it raises `TypeError` at call time. `_RequestRecorder.__call__`
  MUST add `platform=None`; the `_network_forbidden(*args, **kwargs)` and
  `_UrlopenRecorder` fakes already tolerate it. This is the single regression to
  guard against.
- **E6 — no accidental network in verb tests.** The no-token cases must set the
  `_network_forbidden` fake (existing pattern, line 133) to prove `_http_request`
  is NOT called on the no-token path.

---

## Link (validated before building)

- **L1** — Source read in full; all 11 miss ranges mapped to exact constructs
  (see Trace table). Verified line 61, 91-94, 100, 120, 148-162, 185, 222,
  232-239, 244-255, 260-271 against the actual file this session.
- **L2** — `profiles.toml` line 60 confirmed to already list
  `tests/test_broker_pm_platform.py` in `[profile.broker].test`; broker
  coverage already `--cov-branch`. **No Tier-3 amendment needed** (D1).
- **L3** — Existing test file's reusable primitives confirmed present:
  `FAKE_GITHUB_TOKEN`/`FAKE_GITLAB_TOKEN` (lines 53-54), `_RequestRecorder`
  (line 152), the `_network_forbidden` no-token pattern (line 133). Extend, do
  not reinvent.
- **L4** — stdlib seam confirmed: `platform` imports `urllib.request` at module
  top (lines 21-22), so `platform.urllib.request.urlopen` is a patchable module
  attribute. No new import needed in production code.
- **L5** — Convention for module-attr monkeypatching + JSON-string tool results
  cross-checked against `test_broker_pm_mcp_server.py` (`_Recorder`,
  `monkeypatch.setattr(platform, ...)`) and `test_broker_git_mcp_server.py`
  (`monkeypatch.setattr(mcp_server.subprocess, "run", ...)`).
- **L6** — **Bug confirmed and fix blast radius re-verified against source
  (change 3).** `_http_request`'s auth-header selection is at platform.py:150
  (`if "github" in url:`). All 4 call sites pass `_http_request` keyword args
  and hold `remote` in scope (L224, L238, L254, L270), so `platform=remote.platform`
  slots in at each with no positional-arg reshuffle. No other function reads the
  auth header or the `_http_request` signature. The github.com/gitlab.com
  happy-path behavior is unchanged (E7); only the divergent GHE-custom-domain
  case changes (the intended fix).
- **L7** — **Existing-test-double signature impact identified (D9/E8).**
  `_RequestRecorder.__call__` (test line 159) has a fixed kwarg signature and
  MUST gain `platform=None` to accept the new required kwarg; the
  `_network_forbidden(*args, **kwargs)` fake (line 133) already tolerates it.
  This is the only way the fix could break the currently-passing suite, and it
  is addressed in Assemble Step 0.

---

## Assemble (intended build order)

0. **Source fix + test-double signature update (do FIRST, together — D7-D9).**
   (a) Edit `src/gleipnir/broker/pm/platform.py`: add required keyword-only
   `platform: str` to `_http_request`; change line 150-153 to select the auth
   header by `platform == "github"` (Bearer) else PRIVATE-TOKEN; update the 4
   call sites (`issue_create` L224, `issue_update` L238, `issue_comment` L254,
   `issue_close` L270) to pass `platform=remote.platform`. (b) In
   `tests/test_broker_pm_platform.py`, update `_RequestRecorder.__call__` to
   accept and record `platform=None` (D9/E8) so the existing github/gitlab
   `issue_create` happy-path tests still pass. Run the existing suite to confirm
   green BEFORE adding new tests, so any signature-mismatch regression surfaces
   immediately and in isolation.
1. **Append parse/token branch tests** to the existing `TestParseRemoteUrl`
   and `TestTokenResolution` classes (or new sibling classes): ssh:// explicit
   (91-94, +port variant), https-no-match fall-through (89→100), garbage
   fall-through (97→100, line-100 else), empty-path (61), unknown-platform
   token (120). Assert `platform=="gitlab"` on the empty-host cases (E2).
2. **Add `TestApiBaseAndEndpoints`**: GHE github host → `/api/v3` (185); plus a
   github.com base and a gitlab base assertion via `_issues_endpoint` to pin
   both arms and the url-quote of subgroup project paths.
3. **Add `TestHttpRequest`** (the new seam): the 8 cases in the D3 worked
   design, using `_FakeResponse` + `_UrlopenRecorder`, patching
   `platform.urllib.request.urlopen`; case-insensitive header getters (D5/E3);
   **each case passes `platform=` explicitly and asserts the header follows the
   platform arg, not the URL** (D8). Case 8 is the direct-seam fix proof (GHE
   custom domain → Bearer).
4. **Extend the `issue_*` verb tests** using `_RequestRecorder` (D2; recorder
   now records the `platform` kwarg per D9):
   - `issue_create` gitlab-with-body → `description` key (222);
   - `issue_update` no-token (E6) + github PATCH + gitlab PUT (232-239);
   - `issue_comment` no-token + github `/comments` + gitlab `/notes` (244-255);
   - `issue_close` no-token + github `{state:closed}` PATCH + gitlab
     `{state_event:close}` PUT (260-271);
   - assert each verb passes `platform=remote.platform` into `_http_request`.
4b. **Add the full-path GHE fix characterization test (D7, line-150 row):** a
   custom-domain GHE `RemoteInfo` (`host="ghe.corp.example"`, `platform="github"`)
   with `GITHUB_TOKEN` set, driven through `issue_create` with **`urllib`
   mocked (NOT `_http_request`)** so the real header-selection runs; assert the
   sent `Request` carries `Authorization: Bearer <token>` and no `Private-token`
   header — proving the fix end-to-end.
5. **Run** `bin/gleipnir-sandbox test` (broker profile) with coverage; read the
   term-missing report for `platform.py`; confirm ≥85% line+branch and that the
   listed miss ranges are gone.
6. **Confirm** the whole broker suite (including `test_broker_stdlib_only.py`)
   still passes and no live network was opened.

---

## Stress-test (acceptance checks — concrete, checkable)

1. `platform.py` line coverage ≥85% AND branch coverage ≥85% in the broker
   profile term-missing report.
2. The term-missing report for `platform.py` no longer lists any of: 61,
   89→100, 92-94, 97→100, 120, 148-162, 185, 222, 232-239, 244-255, 260-271.
3. `_http_request` tests assert BOTH auth-header variants selected by the
   **`platform` arg** (`Bearer` for `platform="github"`, `PRIVATE-TOKEN`/
   `Private-token` for `platform="gitlab"`), the no-token neither-header case,
   the empty-body `{}` return, and the parsed-JSON non-empty return — all with
   `urllib.request.urlopen` patched, no live network.
4. For each of `_api_base`, `_issues_endpoint`, `issue_create`, `issue_update`,
   `issue_comment`, `issue_close`: both github AND gitlab arms are asserted.
5. Every pre-existing test in `test_broker_pm_platform.py` (parse, token,
   no-token error, github/gitlab issue_create happy paths) still passes — proving
   the `_RequestRecorder` signature update (D9) absorbed the new `platform` kwarg
   with no regression.
6. `test_broker_stdlib_only.py` passes — the fix added no import; platform.py
   stays stdlib-only.
7. `git diff --stat` shows changes to EXACTLY two files:
   `src/gleipnir/broker/pm/platform.py` (the `_http_request` fix + 4 call sites,
   D8) and `tests/test_broker_pm_platform.py`. NO `profiles.toml` change, NO
   `conftest.py` change, NO other `src/**` file touched.
8. Empty-host parse tests assert `platform == "gitlab"` (documents the
   `_detect_platform("")` fall-through, E2).
9. **The GHE fix is proven two ways (D7):** (a) the direct-seam `TestHttpRequest`
   case 8 (`platform="github"` + no-`github`-substring URL → Bearer), and (b)
   the full-path characterization test through `issue_create` with `urllib`
   mocked → Bearer, not PRIVATE-TOKEN. A test asserting the OLD buggy
   PRIVATE-TOKEN behavior for this case is a FAIL (operator chose to fix).
10. The line-61 test uses `"https://github.com/.git"` (path=".git" → empty
    parts), and the `"https://github.com/"` trailing-slash URL is asserted under
    the 89→100 fall-through (not line 61) — the two transcription errors from
    spec-review are corrected.

---

## Execution Workflow (for the implementing agent)

- **Stage/role:** this is now a **coverage + correctness** change (test + one
  source fix, D7-D9). Route the source fix through the appropriate
  implementation stage and the tests through `test`/`gleipnir-code` (Sonnet);
  the tests remain the arbiter, and the two new fix tests (direct-seam +
  full-path) are the correctness arbiter for the fix. Do Assemble Step 0
  (fix + double signature) FIRST and confirm the existing suite still green
  before adding new tests.
- **Edit targets (TWO files):**
  1. `src/gleipnir/broker/pm/platform.py` — add required keyword-only
     `platform: str` to `_http_request`; select the auth header by
     `platform == "github"` (Bearer) else PRIVATE-TOKEN; update all 4 call
     sites to pass `platform=remote.platform` (D8).
  2. `tests/test_broker_pm_platform.py` — append the new tests AND update
     `_RequestRecorder.__call__` to accept/record `platform=None` (D9/E8).
     Reuse the module-level `FAKE_GITHUB_TOKEN`/`FAKE_GITLAB_TOKEN`, the existing
     `_RequestRecorder`, and the `_network_forbidden` no-token pattern. Add the
     two new fakes (`_FakeResponse`, `_UrlopenRecorder`) for the `_http_request`
     seam.
- **Mock boundaries:** `issue_*` verbs → patch `platform._http_request` (D2);
  `_http_request` itself → patch `platform.urllib.request.urlopen` (D3). Never
  open a live socket.
- **Header assertions:** use `request.get_header("Authorization")` /
  `get_header("Private-token")` (case-insensitive) — do NOT match
  `request.headers` by exact key case (D5/E3).
- **URL fixture discipline:** the PRIVATE-TOKEN case MUST use a url with no
  `github` substring (E4); GHE `_api_base` case MUST build `RemoteInfo`
  directly to pin host≠github.com (E5).
- **Run:** `bin/gleipnir-sandbox test` (broker profile) with the coverage args
  already declared in `profiles.toml`. Read term-missing for `platform.py`.
- **Definition of done:** all 10 Stress-test checks green.
- **Scope guard:** the ONLY sanctioned `src/**` change is the `_http_request`
  auth-header fix + the 4 call sites (D8). If implementing the fix seems to
  require touching any other source function, STOP and surface it as a new
  Decision — the operator converged on THIS bug only; do not scope-creep the
  fix.
- **Escalation rule:** if a SECOND, distinct source bug is discovered while
  writing tests, STOP and surface it as a new Decision to the operator — do NOT
  fix it silently in this plan (this plan's sanctioned fix is the GHE
  auth-header bug D7 and nothing else).
- **No profiles.toml/conftest edit** — if any acceptance check seems to require
  one, that is a signal something diverged from this plan; stop and report.

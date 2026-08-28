"""Unit + structural + extensibility tests for the pluggable identity-
resolver seam (`approval/identity/`) and its ONE registered resolver,
`TailscaleResolver`.

Plan: `.gleipnir/plans/tier3-signed-approval.md`, Assemble Step 1,
Stress-test T-12..T-15, T-18. Mirrors
`tests/test_broker_git_content_handlers.py`'s exact style/pattern
(`TestStructuralSafety`, `TestExtensibility`,
`TestRegistrySingleResponsibility`, the `_isolated_registry` fixture) --
see that file for the template this one follows.

**THE DELIBERATE INVERSION (plan Decision 13).** `content_handlers.dispatch`
returns content UNCHANGED on no-match (a benign passthrough). This seam's
`resolve_identity` must instead **raise** `IdentityUnresolved` on no-match
-- there is no safe default identity. `TestFailClosedDispatch` below proves
this inversion is actually implemented, not merely documented.

Test-first note (Axiom 1, restored retroactively): these tests are written
as the correctness arbiter for `src/gleipnir/approval/identity/`; any defect
they surface is fixed in the implementation, not in the test.
"""

from __future__ import annotations

import dataclasses
import inspect
import json
from types import SimpleNamespace

import pytest

from gleipnir.approval.identity import (
    IdentityResolver,
    IdentityUnresolved,
    RequestContext,
    ResolvedIdentity,
    register,
    resolve_identity,
)
from gleipnir.approval.identity import registry as registry_module
from gleipnir.approval.identity.tailscale_resolver import (
    TailscaleResolutionError,
    TailscaleResolver,
)


@pytest.fixture(autouse=True)
def _isolated_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give each test a fresh, empty registry list -- same discipline as
    `test_broker_git_content_handlers.py`'s `_isolated_registry` fixture,
    requiring zero edits to `registry.py`."""
    monkeypatch.setattr(registry_module, "_resolvers", [])


def _fake_run(success_ip: str, login: str = "alice@tailnet"):
    """Build a fake `subprocess.run`-shaped callable: succeeds (returncode 0,
    JSON `UserProfile.LoginName`) only for `success_ip`; fails (non-zero
    exit) for every other remote_ip -- lets tests drive `TailscaleResolver`
    without a real `tailscale` CLI."""

    calls: list[list[str]] = []

    def run(cmd, *, capture_output, text, timeout):  # noqa: ANN001
        calls.append(list(cmd))
        remote_ip = cmd[-1]
        if remote_ip != success_ip:
            return SimpleNamespace(returncode=1, stdout="", stderr="no session")
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"UserProfile": {"LoginName": login}}),
            stderr="",
        )

    run.calls = calls  # type: ignore[attr-defined]
    return run


# ---------------------------------------------------------------------------
# Structural safety, type-level (item 6 / T-12)
# ---------------------------------------------------------------------------


class TestStructuralSafety:
    def test_resolved_identity_has_exactly_identity_and_provider_fields(
        self,
    ) -> None:
        field_names = {f.name for f in dataclasses.fields(ResolvedIdentity)}
        forbidden = {"mac", "token", "change_hash", "key"}
        assert field_names.isdisjoint(forbidden), (
            f"ResolvedIdentity must not expose token/gate fields, found "
            f"{field_names & forbidden}"
        )
        assert field_names == {"identity", "provider"}

    def test_request_context_carries_only_raw_request_facts(self) -> None:
        field_names = {f.name for f in dataclasses.fields(RequestContext)}
        forbidden = {"mac", "token", "change_hash", "key"}
        assert field_names.isdisjoint(forbidden)
        assert field_names == {"remote_ip", "headers"}

    def test_identity_resolver_protocol_exposes_exactly_two_members(self) -> None:
        protocol_members = {
            name for name in dir(IdentityResolver) if not name.startswith("_")
        }
        forbidden = {"mac", "token", "change_hash", "key", "gate"}
        assert protocol_members.isdisjoint(forbidden)
        assert protocol_members == {"can_resolve", "resolve"}

    def test_tailscale_resolver_resolve_signature_is_one_param_returns_identity(
        self,
    ) -> None:
        sig = inspect.signature(TailscaleResolver.resolve)
        params = [p for name, p in sig.parameters.items() if name != "self"]
        assert len(params) == 1, (
            f"resolve() must take exactly one non-self parameter, got {params}"
        )
        (only_param,) = params
        assert only_param.annotation in (RequestContext, "RequestContext")
        assert sig.return_annotation in (ResolvedIdentity, "ResolvedIdentity")

    def test_a_resolver_only_implementing_the_protocol_is_isinstance_checkable(
        self,
    ) -> None:
        """`@runtime_checkable` really is wired -- any object with the right
        two methods satisfies `isinstance(..., IdentityResolver)`, without
        being a `TailscaleResolver` at all."""

        class _Anything:
            def can_resolve(self, request_ctx: RequestContext) -> bool:
                return False

            def resolve(self, request_ctx: RequestContext) -> ResolvedIdentity:
                raise RuntimeError("never called")

        assert isinstance(_Anything(), IdentityResolver)


# ---------------------------------------------------------------------------
# Fail-closed dispatch on no-match (item 7 / T-13) -- THE INVERSION
# ---------------------------------------------------------------------------


class TestFailClosedDispatch:
    def test_resolve_identity_with_empty_registry_raises(self) -> None:
        ctx = RequestContext(remote_ip="10.0.0.1", headers={})
        with pytest.raises(IdentityUnresolved):
            resolve_identity(ctx)

    def test_resolve_identity_with_no_matching_resolver_raises(self) -> None:
        run = _fake_run(success_ip="100.64.0.1")
        register(TailscaleResolver(run=run))
        # This context's remote_ip never matches the fake's success_ip, so
        # can_resolve is False for every registered resolver.
        ctx = RequestContext(remote_ip="203.0.113.9", headers={})
        with pytest.raises(IdentityUnresolved):
            resolve_identity(ctx)

    def test_dispatch_never_returns_a_default_identity(self) -> None:
        """The deliberate inversion vs `content_handlers.dispatch`: no
        unchanged/default-identity fallback value exists -- the no-match
        branch is a raise, not a return."""
        ctx = RequestContext(remote_ip="10.0.0.1", headers={})
        try:
            result = resolve_identity(ctx)
        except IdentityUnresolved:
            return  # expected
        pytest.fail(
            f"resolve_identity must raise on no-match, returned {result!r} instead"
        )


# ---------------------------------------------------------------------------
# Extensibility -- MANDATORY (item 3 / T-14)
# ---------------------------------------------------------------------------


class _DummyOidcResolver:
    """Defined entirely in this test module -- proves registration is pure
    and external: NEITHER `registry.py` NOR `gate.py`/`token.py` needs any
    edit to make this resolver dispatchable. Matches its own context by a
    header, standing in for a future Route-beta OIDC provider."""

    def __init__(self) -> None:
        self.calls: list[RequestContext] = []

    def can_resolve(self, request_ctx: RequestContext) -> bool:
        return request_ctx.headers.get("X-Fake-Provider") == "dummy-oidc"

    def resolve(self, request_ctx: RequestContext) -> ResolvedIdentity:
        self.calls.append(request_ctx)
        return ResolvedIdentity(identity="bob@dummy", provider="dummy-oidc")


class TestExtensibility:
    def test_second_resolver_is_dispatched_for_its_own_context(self) -> None:
        run = _fake_run(success_ip="100.64.0.1")
        register(TailscaleResolver(run=run))
        dummy = _DummyOidcResolver()
        register(dummy)

        ctx = RequestContext(
            remote_ip="203.0.113.9", headers={"X-Fake-Provider": "dummy-oidc"}
        )
        identity = resolve_identity(ctx)
        assert identity == ResolvedIdentity(identity="bob@dummy", provider="dummy-oidc")
        assert dummy.calls == [ctx]

    def test_tailscale_resolver_still_resolves_its_own_context_alongside_dummy(
        self,
    ) -> None:
        run = _fake_run(success_ip="100.64.0.1")
        register(TailscaleResolver(run=run))
        register(_DummyOidcResolver())

        ctx = RequestContext(remote_ip="100.64.0.1", headers={})
        identity = resolve_identity(ctx)
        assert identity == ResolvedIdentity(
            identity="alice@tailnet", provider="tailscale"
        )

    def test_no_edit_to_gate_token_or_registry_was_needed(self) -> None:
        """Documentary assertion: `_DummyOidcResolver` above satisfies the
        `IdentityResolver` protocol using ONLY the public `register`/
        `resolve_identity` surface imported from `identity`. No import of,
        or reference to, an extension point inside `registry.py` is
        required -- their public surface is sufficient for a brand-new
        resolver, exactly like `TestExtensibility` in
        `test_broker_git_content_handlers.py`."""
        assert isinstance(_DummyOidcResolver(), IdentityResolver)


# ---------------------------------------------------------------------------
# Structural source-scan (Design Principles / T-15)
# ---------------------------------------------------------------------------


class TestSingleResponsibilitySourceScan:
    """`registry.py`, `gate.py`, and `token.py` must never name a concrete
    identity provider -- proving the gate/mint/dispatcher are
    provider-agnostic by construction, mirroring
    `TestRegistrySingleResponsibility` in
    `test_broker_git_content_handlers.py`."""

    @pytest.mark.parametrize(
        "module_path",
        [
            "gleipnir.approval.identity.registry",
            "gleipnir.approval.gate",
            "gleipnir.approval.token",
        ],
    )
    def test_module_source_contains_no_concrete_provider_tokens(
        self, module_path: str
    ) -> None:
        import importlib

        mod = importlib.import_module(module_path)
        source = inspect.getsource(mod).lower()
        for forbidden in ("tailscale", "entra", "oidc"):
            assert forbidden not in source, (
                f"{module_path} source contains forbidden provider token "
                f"{forbidden!r} -- violates the provider-agnosticism claim (T-15)"
            )

    def test_registry_module_imports_no_concrete_resolver(self) -> None:
        source = inspect.getsource(registry_module)
        assert "tailscale_resolver" not in source.lower()
        assert "import tailscale" not in source.lower()


# ---------------------------------------------------------------------------
# TailscaleResolver -- the ONE registered resolver (T-18)
# ---------------------------------------------------------------------------


class TestTailscaleResolver:
    def test_can_resolve_true_when_whois_succeeds(self) -> None:
        resolver = TailscaleResolver(run=_fake_run(success_ip="100.64.0.1"))
        ctx = RequestContext(remote_ip="100.64.0.1", headers={})
        assert resolver.can_resolve(ctx) is True

    def test_resolve_returns_login_and_tailscale_provider(self) -> None:
        resolver = TailscaleResolver(
            run=_fake_run(success_ip="100.64.0.1", login="carol@corp.example")
        )
        ctx = RequestContext(remote_ip="100.64.0.1", headers={})
        identity = resolver.resolve(ctx)
        assert identity == ResolvedIdentity(
            identity="carol@corp.example", provider="tailscale"
        )

    def test_can_resolve_false_on_nonzero_exit(self) -> None:
        resolver = TailscaleResolver(run=_fake_run(success_ip="100.64.0.1"))
        ctx = RequestContext(remote_ip="203.0.113.9", headers={})
        assert resolver.can_resolve(ctx) is False

    def test_resolve_raises_on_nonzero_exit(self) -> None:
        resolver = TailscaleResolver(run=_fake_run(success_ip="100.64.0.1"))
        ctx = RequestContext(remote_ip="203.0.113.9", headers={})
        with pytest.raises(TailscaleResolutionError):
            resolver.resolve(ctx)

    def test_resolve_raises_on_unparseable_json(self) -> None:
        def run(cmd, *, capture_output, text, timeout):  # noqa: ANN001
            return SimpleNamespace(returncode=0, stdout="not json", stderr="")

        resolver = TailscaleResolver(run=run)
        with pytest.raises(TailscaleResolutionError):
            resolver.resolve(RequestContext(remote_ip="1.2.3.4", headers={}))

    def test_resolve_raises_on_missing_login_field(self) -> None:
        def run(cmd, *, capture_output, text, timeout):  # noqa: ANN001
            return SimpleNamespace(
                returncode=0, stdout=json.dumps({"UserProfile": {}}), stderr=""
            )

        resolver = TailscaleResolver(run=run)
        with pytest.raises(TailscaleResolutionError):
            resolver.resolve(RequestContext(remote_ip="1.2.3.4", headers={}))

    def test_resolve_raises_on_empty_login(self) -> None:
        def run(cmd, *, capture_output, text, timeout):  # noqa: ANN001
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps({"UserProfile": {"LoginName": ""}}),
                stderr="",
            )

        resolver = TailscaleResolver(run=run)
        with pytest.raises(TailscaleResolutionError):
            resolver.resolve(RequestContext(remote_ip="1.2.3.4", headers={}))

    def test_subprocess_spawn_error_raises_resolution_error_not_default_identity(
        self,
    ) -> None:
        def run(cmd, *, capture_output, text, timeout):  # noqa: ANN001
            raise OSError("tailscale not installed")

        resolver = TailscaleResolver(run=run)
        with pytest.raises(TailscaleResolutionError):
            resolver.resolve(RequestContext(remote_ip="1.2.3.4", headers={}))
        assert resolver.can_resolve(RequestContext(remote_ip="1.2.3.4", headers={})) is False

    def test_invocation_shape_is_exact_argv_with_capture_and_timeout(self) -> None:
        run = _fake_run(success_ip="100.64.0.1")
        resolver = TailscaleResolver(run=run, timeout=2.5)
        resolver.resolve(RequestContext(remote_ip="100.64.0.1", headers={}))
        assert run.calls == [["tailscale", "whois", "--json", "100.64.0.1"]]

    def test_default_provider_constant_is_tailscale(self) -> None:
        from gleipnir.approval.identity.tailscale_resolver import PROVIDER

        assert PROVIDER == "tailscale"

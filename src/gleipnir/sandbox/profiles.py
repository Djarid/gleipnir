"""Config-driven sandbox toolchain-dispatch profiles (Tier-3 POLICY reader).

Spec: `.gleipnir/plans/language-agnostic-sandbox.md` (Trace T1/T3). A pure,
fail-closed reader for `<config_root>/profiles.toml`: parses the
operator-authored TOML, validates every field, and resolves ONE named
profile — never falling back to a silent default command. Mirrors the shape
of `gleipnir.sandbox.runtime` and `gleipnir.preflight.boundary`: a pure,
fully-unit-testable core with the file read as the only thin edge (the
`config_root` path is injected everywhere, never hardcoded past the
production default computed in `__main__.py`).

**STRICT IMAGE RULE (D2/T1) — the cardinal property this module enforces.**
An `image` value is accepted ONLY if it is EITHER

  (a) the exact literal string ``"gleipnir-sandbox:latest"`` (matched by
      **string equality**, the grandfathered self-host image); OR
  (b) a digest-pinned reference matching ``name@sha256:<64 lowercase hex>``
      — exactly one ``@sha256:`` separator, and the part after it exactly
      64 characters, all in ``[0-9a-f]``.

There is deliberately NO rule that accepts an arbitrary ``name:tag`` shape —
that would silently reopen the image-substitution vector D2 exists to close.
Every other value (`someimage:latest`, `myimg:1.2`, a malformed digest, a
non-string, ...) raises `ProfileError`.

**Fail-closed everywhere else too.** Config file missing, malformed TOML,
an unknown profile (by name or via a dangling `default_profile`), a verb
with no configured command, a `test`/`lint` value that is a string instead
of an argv list (or an empty list), and `coverage.unavailable` set without a
non-blank `justified` reason: all raise `ProfileError` — never a silent
default command, never a fabricated/dropped coverage metric.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .runtime import SandboxError

__all__ = [
    "ProfileError",
    "Coverage",
    "Profile",
    "Profiles",
    "load_profiles",
    "resolve_profile",
    "command_for",
]

# The single grandfathered exact-literal image (string equality only — never
# treated as a `name:tag` shape pattern).
_GRANDFATHERED_IMAGE = "gleipnir-sandbox:latest"
_SHA256_SEPARATOR = "@sha256:"
_SHA256_HEX_LEN = 64
_HEX_DIGITS = frozenset("0123456789abcdef")


class ProfileError(SandboxError):
    """Every sandbox-profile-config defect — missing file, malformed TOML,
    unknown profile, a verb with no configured command, an unpinned/invalid
    image, an unjustified coverage-unavailable, a shell-string instead of an
    argv list — raises this. `__main__.py`'s existing `except SandboxError`
    fail-closed exit path catches it uniformly; there is no separate exit
    code for a profile defect."""


@dataclass(frozen=True)
class Coverage:
    """One profile's coverage declaration (D5: honest degradation).

    Either `args` is a non-empty argv-style tuple of extra flags to append
    to the assembled test command (with `file_env`/`file_path` optionally
    routing the coverage data file into the rw scratch mount), OR
    `unavailable` is True with a non-blank `justified` reason. Never
    silently blank in either direction."""

    args: tuple[str, ...] = ()
    file_env: str | None = None
    file_path: str | None = None
    unavailable: bool = False
    justified: str | None = None


@dataclass(frozen=True)
class Profile:
    """One resolved, fully-validated sandbox toolchain profile."""

    name: str
    image: str
    test_argv: tuple[str, ...] = ()
    lint_argv: tuple[str, ...] = ()
    coverage: Coverage = field(default_factory=Coverage)
    test_selector_prefix: bool = False


@dataclass(frozen=True)
class Profiles:
    """Every profile a config declared, plus the configured default name."""

    default_profile: str
    by_name: dict[str, Profile]


# ---------------------------------------------------------------------------
# Field validation — pure, no I/O.
# ---------------------------------------------------------------------------

def _validate_image(image: object, *, profile_name: str) -> str:
    if not isinstance(image, str) or not image:
        raise ProfileError(
            f"profile {profile_name!r}: 'image' must be a non-empty string"
        )
    if image == _GRANDFATHERED_IMAGE:
        return image
    if _SHA256_SEPARATOR in image:
        parts = image.split(_SHA256_SEPARATOR)
        if (
            len(parts) == 2
            and parts[0]
            and len(parts[1]) == _SHA256_HEX_LEN
            and set(parts[1]) <= _HEX_DIGITS
        ):
            return image
    raise ProfileError(
        f"profile {profile_name!r}: image {image!r} is not per the strict "
        f"image rule — accept ONLY the exact literal {_GRANDFATHERED_IMAGE!r} "
        "or a digest-pinned 'name@sha256:<64 lowercase hex>' reference; "
        "refusing rather than accepting an unpinned/arbitrary name:tag "
        "(the image-substitution vector this rule exists to close)"
    )


def _validate_argv(value: object, *, profile_name: str, verb: str) -> tuple[str, ...]:
    if isinstance(value, str):
        raise ProfileError(
            f"profile {profile_name!r}: {verb!r} must be an argv list, never "
            "a shell string (no shell parsing, no compound-command surface)"
        )
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) for item in value)
    ):
        raise ProfileError(
            f"profile {profile_name!r}: {verb!r} must be a non-empty list of "
            "strings"
        )
    return tuple(value)


def _validate_coverage(value: object, *, profile_name: str) -> Coverage:
    if not isinstance(value, dict):
        raise ProfileError(
            f"profile {profile_name!r}: 'coverage' table is required (either "
            "'args' or 'unavailable' + 'justified'); it is never silently "
            "omitted — coverage must always be an honest, explicit choice"
        )

    unavailable = value.get("unavailable", False)
    if unavailable:
        justified = value.get("justified")
        if not isinstance(justified, str) or not justified.strip():
            raise ProfileError(
                f"profile {profile_name!r}: coverage.unavailable=true "
                "requires a non-blank 'justified' reason (D5: never "
                "silently drop the coverage metric)"
            )
        return Coverage(unavailable=True, justified=justified)

    args = value.get("args")
    if (
        not isinstance(args, list)
        or not args
        or not all(isinstance(item, str) for item in args)
    ):
        raise ProfileError(
            f"profile {profile_name!r}: coverage.args must be a non-empty "
            "list of strings when coverage is not declared unavailable"
        )
    file_env = value.get("file_env")
    file_path = value.get("file_path")
    if file_env is not None and not isinstance(file_env, str):
        raise ProfileError(
            f"profile {profile_name!r}: coverage.file_env must be a string"
        )
    if file_path is not None and not isinstance(file_path, str):
        raise ProfileError(
            f"profile {profile_name!r}: coverage.file_path must be a string"
        )
    return Coverage(args=tuple(args), file_env=file_env, file_path=file_path)


# ---------------------------------------------------------------------------
# Config load — the one thin edge (reads exactly one file).
# ---------------------------------------------------------------------------

def load_profiles(config_root: Path) -> Profiles:
    """Read and fully validate `<config_root>/profiles.toml`.

    `config_root` is ALWAYS an explicit parameter (never resolved from an
    env var or CLI flag by this function) — production callers pass the
    fixed Tier-3 default; tests pass a `tests/`-local fixture root. Every
    defect raises `ProfileError`; there is no partial/default success."""

    config_path = Path(config_root) / "profiles.toml"
    try:
        raw = config_path.read_bytes()
    except OSError as exc:
        raise ProfileError(
            f"sandbox profile config not found at {config_path}; the "
            "operator must author it (Tier-3 policy) — never defaulting to "
            "an implicit command"
        ) from exc

    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ProfileError(
            f"sandbox profile config at {config_path} is not valid UTF-8: {exc}"
        ) from exc
    except tomllib.TOMLDecodeError as exc:
        raise ProfileError(
            f"sandbox profile config at {config_path} is malformed TOML: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ProfileError(
            f"sandbox profile config at {config_path} must be a TOML table "
            "at the top level"
        )

    default_profile = data.get("default_profile")
    if not isinstance(default_profile, str) or not default_profile:
        raise ProfileError(
            f"sandbox profile config at {config_path} must declare a "
            "non-empty string 'default_profile'"
        )

    profile_table = data.get("profile")
    if not isinstance(profile_table, dict) or not profile_table:
        raise ProfileError(
            f"sandbox profile config at {config_path} declares no "
            "[profile.*] tables"
        )

    by_name: dict[str, Profile] = {}
    for name, entry in profile_table.items():
        if not isinstance(entry, dict):
            raise ProfileError(
                f"sandbox profile config at {config_path}: profile {name!r} "
                "must be a table"
            )

        image = _validate_image(entry.get("image"), profile_name=name)

        test_argv: tuple[str, ...] = ()
        if "test" in entry:
            test_argv = _validate_argv(entry["test"], profile_name=name, verb="test")

        lint_argv: tuple[str, ...] = ()
        if "lint" in entry:
            lint_argv = _validate_argv(entry["lint"], profile_name=name, verb="lint")

        coverage = _validate_coverage(entry.get("coverage"), profile_name=name)

        test_selector_prefix = entry.get("test_selector_prefix", False)
        if not isinstance(test_selector_prefix, bool):
            raise ProfileError(
                f"profile {name!r}: 'test_selector_prefix' must be a bool"
            )

        by_name[name] = Profile(
            name=name,
            image=image,
            test_argv=test_argv,
            lint_argv=lint_argv,
            coverage=coverage,
            test_selector_prefix=test_selector_prefix,
        )

    if default_profile not in by_name:
        raise ProfileError(
            f"sandbox profile config at {config_path}: default_profile "
            f"{default_profile!r} names a profile that is not defined "
            f"(defined: {sorted(by_name)})"
        )

    return Profiles(default_profile=default_profile, by_name=by_name)


def resolve_profile(profiles: Profiles, name: str | None = None) -> Profile:
    """Resolve one named profile, or `profiles.default_profile` if `name` is
    `None`. Never silently substitutes a different profile."""

    target = name if name is not None else profiles.default_profile
    try:
        return profiles.by_name[target]
    except KeyError as exc:
        raise ProfileError(
            f"sandbox profile {target!r} is not defined "
            f"(defined: {sorted(profiles.by_name)})"
        ) from exc


def command_for(profile: Profile, verb: str) -> tuple[str, ...]:
    """The configured argv HEAD for `verb` ('test' or 'lint'). Raises
    `ProfileError` if the profile has no command configured for that verb —
    NEVER a silent default command."""

    argv = profile.test_argv if verb == "test" else profile.lint_argv
    if not argv:
        raise ProfileError(
            f"profile {profile.name!r} has no configured command for verb "
            f"{verb!r}; refusing rather than falling back to a silent "
            "default command"
        )
    return argv

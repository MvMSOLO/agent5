"""Semantic version parsing and comparison (semver.org 2.0.0 subset).

This module intentionally implements only the precedence rules from the
semver 2.0.0 specification:

    * Major/minor/patch compare numerically.
    * A pre-release version has lower precedence than its associated
      normal version (``1.0.0-alpha < 1.0.0``).
    * Pre-release identifiers compare left-to-right: numeric identifiers
      compare numerically and always sort before alphanumeric ones; a
      larger set of identifiers sorts after a matching smaller prefix
      (``1.0.0-alpha < 1.0.0-alpha.1``).
    * Build metadata is ignored for precedence (``1.0.0+a == 1.0.0+b``).
"""

from __future__ import annotations

import re
from functools import total_ordering
from typing import Iterable

from agent5.validators import ValidationError, validate_semver

__all__ = ["SemVer", "compare_versions", "sort_versions"]

_SEMVER_RE = re.compile(
    r"\A(?P<major>0|[1-9]\d*)"
    r"\.(?P<minor>0|[1-9]\d*)"
    r"\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>"
    r"(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+(?P<buildmetadata>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?\Z"
)


@total_ordering
class SemVer:
    """An immutable parsed semantic version."""

    __slots__ = ("major", "minor", "patch", "prerelease", "build")

    def __init__(self, version_string: str) -> None:
        validated = validate_semver(version_string)
        match = _SEMVER_RE.match(validated)
        assert match is not None  # guaranteed by validate_semver
        self.major: int = int(match.group("major"))
        self.minor: int = int(match.group("minor"))
        self.patch: int = int(match.group("patch"))
        pre = match.group("prerelease")
        self.prerelease: tuple[str, ...] = tuple(pre.split(".")) if pre else ()
        build = match.group("buildmetadata")
        self.build: str | None = build

    @classmethod
    def parse(cls, version_string: str) -> "SemVer":
        """Alias constructor mirroring common ``parse`` APIs."""
        return cls(version_string)

    @property
    def is_prerelease(self) -> bool:
        return bool(self.prerelease)

    def _core(self) -> tuple[int, int, int]:
        return (self.major, self.minor, self.patch)

    def _pre_key(self) -> tuple:
        """Sort key implementing semver pre-release precedence rules.

        Versions without a pre-release sort *after* versions with one for
        the same core number, so every key starts with a flag element:
        ``(1, ...)`` for release versions (no pre-release) and ``(0, ...)``
        for pre-releases. Each identifier then becomes ``(0, int_value)``
        when numeric or ``(1, string_value)`` when alphanumeric, which
        enforces 'numeric identifiers always have lower precedence than
        non-numeric'. Because all keys are tuples of the same shape
        (flag first), Python's lexicographic tuple comparison is safe and
        shorter matching prefixes sort first (``alpha < alpha.1``).
        """
        if not self.prerelease:
            # No pre-release sorts after any pre-release of the same core.
            return ((2,),)
        keys: list = []
        for ident in self.prerelease:
            if ident.isdigit():
                keys.append((0, int(ident), ""))
            else:
                keys.append((1, 0, ident))
        return tuple(keys)

    def _cmp_tuple(self) -> tuple:
        return (self._core(), self._pre_key())

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SemVer):
            return self._cmp_tuple() == other._cmp_tuple()
        return NotImplemented

    def __lt__(self, other: "SemVer") -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return self._cmp_tuple() < other._cmp_tuple()

    def __hash__(self) -> int:
        return hash(self._cmp_tuple())

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            base += "-" + ".".join(self.prerelease)
        if self.build:
            base += "+" + self.build
        return base

    def __repr__(self) -> str:
        return f"SemVer({str(self)!r})"


def compare_versions(a: str, b: str) -> int:
    """Return -1, 0, or 1 comparing semver strings ``a`` and ``b``.

    Raises:
        ValidationError: if either string is not valid semver.
    """
    va, vb = SemVer(a), SemVer(b)
    if va < vb:
        return -1
    if vb < va:
        return 1
    return 0


def sort_versions(versions: Iterable[str]) -> list[str]:
    """Return ``versions`` sorted ascending by semver precedence.

    Raises:
        ValidationError: if any element is not valid semver.
    """
    items = list(versions)
    parsed = [SemVer(v) for v in items]
    order = sorted(range(len(items)), key=lambda i: parsed[i])
    return [items[i] for i in order]

"""Tests for agent5.semver — precedence rules from semver.org 2.0.0."""

import pytest

from agent5.semver import SemVer, compare_versions, sort_versions
from agent5.validators import ValidationError

# Canonical ascending-precedence example from the semver 2.0.0 spec.
SPEC_ORDER = [
    "1.0.0-alpha",
    "1.0.0-alpha.1",
    "1.0.0-alpha.beta",
    "1.0.0-beta",
    "1.0.0-beta.2",
    "1.0.0-beta.11",
    "1.0.0-rc.1",
    "1.0.0",
]


class TestParsing:
    def test_core_fields(self):
        v = SemVer("1.2.3")
        assert (v.major, v.minor, v.patch) == (1, 2, 3)
        assert v.prerelease == ()
        assert v.build is None
        assert not v.is_prerelease

    def test_prerelease_and_build(self):
        v = SemVer("1.0.0-beta.11+exp.sha.5114f85")
        assert v.prerelease == ("beta", "11")
        assert v.build == "exp.sha.5114f85"
        assert v.is_prerelease

    def test_roundtrip_str(self):
        for s in ["0.0.0", "10.20.30", "1.0.0-alpha.1", "1.0.0+a.b",
                  "1.0.0-rc.1+build.99"]:
            assert str(SemVer(s)) == s

    def test_invalid_raises(self):
        with pytest.raises(ValidationError):
            SemVer("not.a.version")


class TestPrecedence:
    def test_spec_example_chain(self):
        for lower, higher in zip(SPEC_ORDER, SPEC_ORDER[1:]):
            assert SemVer(lower) < SemVer(higher), f"{lower} < {higher}"
            assert compare_versions(lower, higher) == -1
            assert compare_versions(higher, lower) == 1

    def test_numeric_core_precedence(self):
        assert SemVer("2.0.0") > SemVer("1.99.99")
        assert SemVer("1.10.0") > SemVer("1.9.0")
        assert SemVer("1.0.10") > SemVer("1.0.9")

    def test_build_metadata_ignored(self):
        assert SemVer("1.0.0+a") == SemVer("1.0.0+b")
        assert compare_versions("1.0.0+build.1", "1.0.0+build.2") == 0
        assert hash(SemVer("1.0.0+a")) == hash(SemVer("1.0.0+b"))

    def test_equality_reflexive(self):
        assert SemVer("1.2.3-x") == SemVer("1.2.3-x")
        assert compare_versions("1.2.3", "1.2.3") == 0

    def test_comparison_with_non_semver_returns_notimplemented(self):
        with pytest.raises(TypeError):
            SemVer("1.0.0") < "1.0.0"  # type: ignore[comparison-overlap]

    def test_usable_as_dict_key_and_in_set(self):
        versions = {SemVer("1.0.0"), SemVer("1.0.0+build")}
        assert len(versions) == 1


class TestSortVersions:
    def test_sorts_spec_order(self):
        shuffled = list(reversed(SPEC_ORDER))
        assert sort_versions(shuffled) == SPEC_ORDER

    def test_stable_for_equal_precedence(self):
        result = sort_versions(["1.0.0+b", "1.0.0+a"])
        assert result == ["1.0.0+b", "1.0.0+a"]  # equal -> original order kept

    def test_empty_input(self):
        assert sort_versions([]) == []

    def test_invalid_member_raises(self):
        with pytest.raises(ValidationError):
            sort_versions(["1.0.0", "oops"])

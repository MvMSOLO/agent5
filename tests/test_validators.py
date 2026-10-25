"""Tests for agent5.validators — happy paths, edge cases, failure modes."""

import pytest

from agent5.validators import (
    MAX_EMAIL_LENGTH,
    MAX_LOCAL_PART_LENGTH,
    MAX_URL_LENGTH,
    ValidationError,
    safe_int,
    validate_email,
    validate_semver,
    validate_url,
)


class TestValidateEmail:
    @pytest.mark.parametrize(
        "email,expected",
        [
            ("user@example.com", "user@example.com"),
            ("User@Example.COM", "user@example.com"),
            ("  spaced@example.com  ", "spaced@example.com"),
            ("first.last@sub.domain.org", "first.last@sub.domain.org"),
            ("tag+filter@example.com", "tag+filter@example.com"),
            ("o'brien@example.io", "o'brien@example.io"),
            ("a" * MAX_LOCAL_PART_LENGTH + "@example.com",
             "a" * MAX_LOCAL_PART_LENGTH + "@example.com"),
        ],
    )
    def test_valid(self, email, expected):
        assert validate_email(email) == expected

    @pytest.mark.parametrize(
        "bad",
        [
            "",
            "   ",
            "no-at-sign.example.com",
            "@example.com",                      # empty local part
            ("x" * (MAX_LOCAL_PART_LENGTH + 1)) + "@example.com",  # long local
            "a" * (MAX_EMAIL_LENGTH + 1) + "@example.com",         # long total
            "two@@at.com",
            ".leading-dot@example.com",
            "trailing-dot.@example.com",
            "double..dot@example.com",
            "missing@tld",                       # no dot in domain
            "user@domain.c",                     # 1-char TLD
            "user@-hyphenstart.com",
            "user@hyphenend-.com",
            "user@dom ain.com",                  # space in domain
            "user@domain.com.",                  # trailing dot -> empty label
        ],
    )
    def test_invalid_strings(self, bad):
        with pytest.raises(ValidationError):
            validate_email(bad)

    @pytest.mark.parametrize("bad", [None, 42, 3.14, b"bytes@example.com", ["a@b.co"]])
    def test_non_string_input(self, bad):
        with pytest.raises(ValidationError, match="must be a string"):
            validate_email(bad)

    def test_error_is_valueerror(self):
        # Backwards-compat guarantee: callers catching ValueError still work.
        with pytest.raises(ValueError):
            validate_email("not-an-email")


class TestValidateUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com",
            "http://example.com/path?q=1#frag",
            "https://user:pass@example.com:8443/x",
            "ftp://files.example.com/pub",
            "mailto:someone@example.com",
            "git@github.com:user/repo.git".replace("git@", "ssh://git@"),
            "https://xn--80ak6aa92e.com",  # punycode host
            "https://192.168.1.1",
            "https://[2001:db8::1]:443/ipv6",
        ],
    )
    def test_valid(self, url):
        assert validate_url(url) == url

    @pytest.mark.parametrize(
        "bad",
        [
            "",
            "   ",
            "example.com",                        # missing scheme
            "//example.com",                      # scheme-relative
            "javascript:alert(1)",                # XSS vector
            "JaVaScRiPt:alert(1)",                # case-obfuscated XSS
            "data:text/html,<script>alert(1)</script>",
            "file:///etc/passwd",
            "https://",                           # empty host
            "http:/example.com",                  # no netloc
            "https://exa mple.com",               # unparseable (space in host)
            "https://" + "a" * MAX_URL_LENGTH,    # too long
        ],
    )
    def test_invalid(self, bad):
        with pytest.raises(ValidationError):
            validate_url(bad)

    def test_custom_allowlist(self):
        assert validate_url("javascript:x", allowed_schemes=frozenset({"javascript"}))
        with pytest.raises(ValidationError, match="not allowed"):
            validate_url("https://ok.com", allowed_schemes=frozenset({"ftp"}))

    def test_non_string(self):
        with pytest.raises(ValidationError, match="must be a string"):
            validate_url(None)


class TestValidateSemver:
    @pytest.mark.parametrize(
        "v",
        [
            "0.0.0",
            "1.2.3",
            "10.20.30",
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0-0.3.7",
            "1.0.0-x.7.z.92",
            "1.0.0+build.1",
            "1.0.0-beta+exp.sha.5114f85",
            "1.0.0-rc.1+build.1",
        ],
    )
    def test_valid(self, v):
        assert validate_semver(v) == v

    @pytest.mark.parametrize(
        "bad",
        [
            "",
            "1",
            "1.2",
            "1.2.3.4",
            "v1.2.3",                 # leading v not allowed by spec
            "01.2.3",                 # leading zero
            "1.02.3",
            "1.2.03",
            "1.2.3-01",               # numeric prerelease with leading zero
            "1.2.3+",                 # empty build
            "1.2.3-",                 # empty prerelease
            "1.2.3-alpha..1",         # empty identifier
            "1.2.3 ",
            "-1.2.3",
        ],
    )
    def test_invalid(self, bad):
        with pytest.raises(ValidationError):
            validate_semver(bad)


class TestSafeInt:
    @pytest.mark.parametrize(
        "value,expected",
        [(0, 0), (-5, -5), (2**70, 2**70), ("42", 42), (" -7 ", -7)],
    )
    def test_valid(self, value, expected):
        assert safe_int(value) == expected

    @pytest.mark.parametrize(
        "bad",
        [True, False, None, 3.5, "abc", "", "1.5", [], {}, object()],
    )
    def test_invalid(self, bad):
        with pytest.raises(ValidationError):
            safe_int(bad)

    def test_bounds(self):
        assert safe_int("5", minimum=0, maximum=10) == 5
        with pytest.raises(ValidationError, match=">= 0"):
            safe_int(-1, minimum=0)
        with pytest.raises(ValidationError, match="<= 10"):
            safe_int(11, maximum=10)

    def test_field_name_in_message(self):
        with pytest.raises(ValidationError, match="port"):
            safe_int("nope", field="port")

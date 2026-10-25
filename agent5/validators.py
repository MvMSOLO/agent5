"""Input validation helpers.

Design goals:
    * No third-party dependencies.
    * Predictable, documented behavior for edge cases (empty strings,
      non-string inputs, unicode, overflow).
    * Every public function either returns a cleaned value or raises
      :class:`ValidationError` with an actionable message.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

__all__ = [
    "ValidationError",
    "validate_email",
    "validate_url",
    "validate_semver",
    "safe_int",
]

# Maximum lengths chosen to match common practical limits (RFC 5321
# caps the total path at 254 octets; email local-part at 64).
MAX_EMAIL_LENGTH = 254
MAX_LOCAL_PART_LENGTH = 64
MAX_URL_LENGTH = 2048

# Deliberately conservative email pattern: rejects leading/trailing/
# consecutive dots in the local part, requires a domain with at least one
# dot and an alphabetic TLD of length >= 2. Internationalized domains are
# accepted at the syntax level only if ASCII-label rules hold.
_EMAIL_LOCAL_RE = re.compile(
    r"^[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+"
    r"(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*$"
)
_DOMAIN_LABEL_RE = re.compile(
    r"^(?=.{1,63}$)[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$"
)
_TLD_RE = re.compile(r"^[A-Za-z]{2,}$")

_SEMVER_RE = re.compile(
    r"\A(?P<major>0|[1-9]\d*)"
    r"\.(?P<minor>0|[1-9]\d*)"
    r"\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>"
    r"(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+(?P<buildmetadata>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?\Z"
)

_ALLOWED_SCHEMES = frozenset({"http", "https", "ftp", "ftps", "mailto", "git", "ssh"})


class ValidationError(ValueError):
    """Raised when input fails validation.

    Inherits from ``ValueError`` so existing callers that catch
    ``ValueError`` keep working.
    """


def _require_str(value: object, field: str) -> str:
    if isinstance(value, str):
        return value
    raise ValidationError(f"{field} must be a string, got {type(value).__name__}")


def validate_email(email: object) -> str:
    """Return ``email`` lowercased if it is a syntactically valid address.

    Raises:
        ValidationError: if the input is not a string, exceeds length
            limits, or is not a valid email address.
    """
    value = _require_str(email, "email").strip()
    if not value:
        raise ValidationError("email must not be empty")
    if len(value) > MAX_EMAIL_LENGTH:
        raise ValidationError(
            f"email exceeds maximum length of {MAX_EMAIL_LENGTH} characters"
        )
    local, sep, domain = value.rpartition("@")
    if not sep:
        raise ValidationError("email must contain exactly one '@' separator")
    if "@" in local or "@" in domain:
        raise ValidationError("email must contain exactly one '@' separator")
    if not local:
        raise ValidationError("email local part must not be empty")
    if len(local) > MAX_LOCAL_PART_LENGTH:
        raise ValidationError(
            f"email local part exceeds {MAX_LOCAL_PART_LENGTH} characters"
        )
    if not _EMAIL_LOCAL_RE.match(local):
        raise ValidationError("email local part contains invalid characters")
    labels = domain.split(".")
    if len(labels) < 2:
        raise ValidationError("email domain must contain at least one dot")
    for label in labels[:-1]:
        if not _DOMAIN_LABEL_RE.match(label):
            raise ValidationError(
                f"email domain label {label!r} is invalid (must be 1-63 chars, "
                "alphanumeric or hyphen, not starting or ending with a hyphen)"
            )
    tld = labels[-1]
    if not _TLD_RE.match(tld):
        raise ValidationError(
            "email top-level domain must be alphabetic and at least 2 characters"
        )
    return value.lower()


def validate_url(url: object, allowed_schemes: frozenset[str] | None = None) -> str:
    """Return ``url`` stripped if it is a valid URL with an allowed scheme.

    The default allow-list blocks dangerous pseudo-schemes such as
    ``javascript:``, ``data:``, and ``file:`` that are common XSS vectors
    when URLs are rendered in HTML.

    Raises:
        ValidationError: on malformed input, disallowed scheme, missing
            network location (for http(s)/ftp style URLs), or excessive
            length.
    """
    value = _require_str(url, "url").strip()
    if not value:
        raise ValidationError("url must not be empty")
    if len(value) > MAX_URL_LENGTH:
        raise ValidationError(
            f"url exceeds maximum length of {MAX_URL_LENGTH} characters"
        )
    schemes = allowed_schemes if allowed_schemes is not None else _ALLOWED_SCHEMES
    try:
        parsed = urlparse(value)
    except ValueError as exc:  # e.g. invalid IPv6 brackets
        raise ValidationError(f"url could not be parsed: {exc}") from exc
    scheme = parsed.scheme.lower()
    if not scheme:
        raise ValidationError("url must include a scheme (e.g. 'https://')")
    if scheme not in schemes:
        raise ValidationError(
            f"url scheme {scheme!r} is not allowed; "
            f"allowed schemes: {sorted(schemes)}"
        )
    if scheme in ("http", "https", "ftp", "ftps"):
        if not parsed.netloc:
            raise ValidationError(f"{scheme} urls must include a network location")
        try:
            host = parsed.hostname
        except ValueError as exc:  # e.g. invalid IPv6 brackets
            raise ValidationError(f"url host could not be parsed: {exc}") from exc
        if not host:
            raise ValidationError("url host must not be empty")
        if ".." in host:
            raise ValidationError("url host must not contain '..'")
        # Reject characters that urlparse does not police but that break
        # downstream consumers (whitespace, control chars, backslashes).
        if re.search(r"[\s\\/]", host):
            raise ValidationError("url host contains invalid characters")
    return value


def validate_semver(version: object) -> str:
    """Return ``version`` unchanged if it matches the semver 2.0.0 grammar.

    Accepts forms like ``1.2.3``, ``1.0.0-alpha.1``,
    ``2.1.0-beta+exp.sha.5114f85``. Rejects leading zeros in numeric
    identifiers per the spec.

    Raises:
        ValidationError: if the string is not valid semver.
    """
    value = _require_str(version, "version")
    if value != value.strip():
        raise ValidationError("version must not have leading or trailing whitespace")
    if not value:
        raise ValidationError("version must not be empty")
    if not _SEMVER_RE.match(value):
        raise ValidationError(
            f"{value!r} is not a valid semantic version "
            "(expected MAJOR.MINOR.PATCH per semver.org 2.0.0)"
        )
    return value


def safe_int(
    value: object,
    *,
    field: str = "value",
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """Coerce ``value`` to an ``int`` with explicit error handling.

    Accepts ``int`` and strings that represent integers. Booleans are
    intentionally rejected because ``True``/``False`` silently coercing to
    ``1``/``0`` hides bugs at input boundaries. Floats are rejected to
    avoid silent truncation.

    Raises:
        ValidationError: if coercion is impossible or bounds are violated.
    """
    if isinstance(value, bool):
        raise ValidationError(f"{field} must be an integer, got a boolean")
    result: int
    if isinstance(value, int):
        result = value
    elif isinstance(value, str):
        text = value.strip()
        try:
            result = int(text)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{field} {value!r} is not an integer") from exc
    else:
        raise ValidationError(
            f"{field} must be an int or numeric string, got {type(value).__name__}"
        )
    if minimum is not None and result < minimum:
        raise ValidationError(f"{field} must be >= {minimum}, got {result}")
    if maximum is not None and result > maximum:
        raise ValidationError(f"{field} must be <= {maximum}, got {result}")
    return result

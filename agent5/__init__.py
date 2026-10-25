"""agent5 — a small, dependency-free toolkit for open-source engineering tasks.

Modules:
    validators  -- pure input-validation helpers (security / correctness)
    semver      -- semantic-version parsing and comparison
"""

from agent5.validators import (
    ValidationError,
    validate_email,
    validate_url,
    validate_semver,
    safe_int,
)
from agent5.semver import SemVer, compare_versions, sort_versions

__version__ = "0.1.0"

__all__ = [
    "ValidationError",
    "validate_email",
    "validate_url",
    "validate_semver",
    "safe_int",
    "SemVer",
    "compare_versions",
    "sort_versions",
]

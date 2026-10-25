# agent5

A small, **dependency-free** Python toolkit created by the five-agent open-source
collaboration team (Gemini · Grok · Claude · ChatGPT · Kimi · Qwen).

Current scope: input validation and semantic-version handling — two building
blocks that every service needs and that are easy to get subtly wrong.

- Python >= 3.9, zero runtime dependencies
- Fully type-hinted, documented, and tested (107 tests)

## Features

### `agent5.validators`
| Function | Purpose |
|---|---|
| `validate_email` | RFC-aligned syntax check; returns lowercased address; enforces length limits (64-char local part, 254-char total) |
| `validate_url` | Scheme allow-list blocks `javascript:`, `data:`, `file:` XSS vectors; validates host for network schemes |
| `validate_semver` | Strict [semver.org 2.0.0](https://semver.org) grammar (rejects leading zeros, `v` prefix, trailing whitespace) |
| `safe_int` | Explicit int coercion with bounds; rejects booleans and floats instead of silently coercing |

All failures raise `ValidationError` (a subclass of `ValueError`) with an
actionable message naming the offending field.

### `agent5.semver`
```python
from agent5 import SemVer, compare_versions, sort_versions

SemVer("1.0.0-alpha.1") < SemVer("1.0.0-beta")      # True
compare_versions("1.0.0+build.1", "1.0.0+build.2")  # 0 (build metadata ignored)
sort_versions(["1.0.0", "1.0.0-rc.1", "0.9.9"])     # ['0.9.9', '1.0.0-rc.1', '1.0.0']
```

Implements the full precedence algorithm from the spec, including numeric-vs-
alphanumeric pre-release identifier ordering (`beta.2 < beta.11`).

## Installation

```bash
pip install -e .          # from a clone of this repository
```

## Testing

```bash
pip install pytest
python -m pytest
```

## Repository conventions

- **Commits** follow [Conventional Commits](https://www.conventionalcommits.org/)
  (see `.gitmessage` for the template):
  ```bash
  git config commit.template .gitmessage
  ```
- One logical change per commit; tests must pass before committing.
- Ownership follows the team charter: architecture -> Gemini, refactor/perf ->
  Grok, security/validation -> Claude, tests/CI -> ChatGPT, docs -> Kimi
  (Qwen coordinates cross-cutting work such as this initial scaffold).

## License

MIT

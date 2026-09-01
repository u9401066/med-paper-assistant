# Test suite

The suite is grouped by the behavior it protects, not by implementation class.

| Layer            | Marker / location                           | Purpose                                                                                                      |
| ---------------- | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Fast behavior    | `tests/test_*.py`                           | Domain, application, persistence, and local adapter outcomes; default CI path                                |
| Contract         | `contract`                                  | Public MCP surfaces, release wiring, docs, locks, and repository invariants                                  |
| MCP protocol     | `mcp`                                       | Official SDK client/server initialize, discovery, elicitation, progress, cancellation, and shutdown behavior |
| Product smoke    | `smoke`                                     | Real process, package, or representative end-to-end paths                                                    |
| External / heavy | `integration`, `slow`, `tests/integration/` | Network, archive-install, or optional native-package checks                                                  |

Canonical commands:

```bash
uv run pytest tests/ -q -m "not integration and not slow"
uv run pytest tests/ -q -m contract
uv run pytest tests/ -q -m mcp
uv run pytest tests/ -q -m smoke
uv run pytest tests/integration/test_watermark_package_smoke.py -q -m integration
uv run pytest tests/integration/test_zotero_sdk2_install_smoke.py -q -m "integration and slow"
```

Coverage reports are diagnostic evidence, not a reason to manufacture tests. A repository-wide threshold is a hard gate only when it is declared in `pyproject.toml` and enforced by CI. For a focused patch, require direct behavioral or integration coverage of the changed production path and report the full-suite baseline honestly.

Tests must call production code or an executable artifact and assert an observable outcome. Do not add tests that only round-trip Python's standard library, inspect a dictionary created inside the same test, repeat a constant without exercising its consumer, print PASS/FAIL without asserting, or swallow exceptions. Prefer one table-driven boundary test over repeated single-case tests.

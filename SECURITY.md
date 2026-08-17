# Security Policy

## Supported versions

| Version | Security support                                                 |
| ------- | ---------------------------------------------------------------- |
| `0.9.x` | Current supported line                                           |
| `<0.9`  | Not supported; upgrade before reporting a version-specific issue |

Only the latest patch release in the supported line receives security fixes. The repository may contain unreleased work; a branch build is not a supported release unless its exact commit is provided in the report.

## Report a vulnerability privately

Do not open a public issue for an unpatched vulnerability or include secrets, private datasets, patient information, or exploit details in public discussions.

Use the repository's [private vulnerability reporting form](https://github.com/u9401066/med-paper-assistant/security/advisories/new) when GitHub makes it available. If the form is unavailable, contact the repository owner through their GitHub profile to request a private channel without including vulnerability details in the public message. Maintainers should enable private vulnerability reporting before the next release.

Include:

- affected version, commit, operating system, Python/Node versions, and MCP client;
- the smallest reproducible input and exact commands;
- impact, required privileges, and whether network or filesystem access is involved;
- logs with credentials and sensitive research data removed;
- a suggested mitigation, if known.

Maintainers will respond on a best-effort basis. This project does not currently promise a fixed acknowledgement or remediation SLA. After triage, maintainers will coordinate disclosure and credit through the private advisory.

## Relevant security scope

Reports are especially useful for path traversal or unintended file access, command injection, MCP tool or prompt injection that crosses a documented trust boundary, credential leakage, unsafe archive/document parsing, dependency or release-chain compromise, and authorization bypass of protected artifacts.

Unsupported scientific claims, citation mistakes, or visible/provenance watermark findings are normally quality or research-integrity issues rather than software vulnerabilities. Report them through the normal issue workflow unless they also expose data, execute code, or bypass a security boundary.

## Current security practices and limits

- Python and Node dependencies are locked and CI runs Ruff, mypy, Bandit, tests, package/install smoke, and `npm audit` where configured.
- PyPI and VS Code Marketplace publishing use GitHub OIDC trusted publishing. The Marketplace publisher must keep the repository/environment trust policy configured; no long-lived `VSCE_PAT` is required by the release workflow.
- Credentials belong in environment variables or GitHub secrets and must never be committed. Local MCP configuration may reference secret names, not secret values.
- Automated Dependabot update configuration is not currently present. Lockfiles and CI reduce drift but do not imply continuous vulnerability monitoring; dependency review must be performed for releases and advisories.
- Optional document and C2PA adapters expand the parsing surface. Missing optional dependencies must degrade explicitly; provenance inspection is read-only and verifies the asset hash before and after inspection.
- A valid C2PA manifest proves only the validated signed assertions under the available trust configuration. It does not prove scientific truth, copyright permission, or harmless content; an absent manifest is not evidence of compromise.

See [MCP 2 and content integrity](docs/wiki/mcp2-content-integrity.md) for the asset gate and [development and release](docs/wiki/development-and-release.md) for release checks.

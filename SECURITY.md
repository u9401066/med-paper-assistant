# Security Policy

## Supported Versions

| Version | Supported  |
| ------- | ---------- |
| 0.3.x   | ✅ Current |
| < 0.3   | ❌ No      |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **DO NOT** open a public GitHub Issue
2. Email: medpaper-security@example.com
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will acknowledge receipt within 48 hours and aim to release a fix within 7 days for critical issues.

## Security Practices

- **Trusted Publishing**: PyPI releases use OIDC trusted publishing (no stored API tokens)
- **Pre-commit hooks**: All commits pass ruff, mypy, bandit security scans
- **Dependency scanning**: Dependabot monitors for vulnerable dependencies
- **No secrets in code**: All credentials stored in GitHub Secrets or environment variables

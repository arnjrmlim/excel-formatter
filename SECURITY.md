# Security Policy

## Supported Versions

Security updates are supported for the current `main` branch unless a separate release policy is created.

## Reporting a Vulnerability

Please report suspected vulnerabilities privately to the repository owner or maintainer. Do not open a public issue for sensitive security reports.

Include:

- A clear description of the issue.
- Steps to reproduce the behavior.
- Impact and affected files or versions.
- Any suggested remediation, if known.

## Responsible Disclosure

Maintainers will review reports as promptly as possible, validate the issue, and coordinate a fix before public disclosure when appropriate.

## Security Practices

- Do not commit secrets, `.env` files, logs, generated workbooks, or executable build outputs.
- Keep dependencies reviewed and updated.
- Treat source workbooks and exported files as sensitive business data.
- Run the Windows macro helper only from trusted source code or trusted release artifacts.
- Keep local control services bound to loopback addresses unless a formal security review approves a broader network surface.
- Publish IMS TinyTask executables only through trusted GitHub Releases, and keep the release asset name as `IMS_tinytask.exe` so the formatter can use GitHub's latest-release download endpoint.
- Do not add local absolute paths, usernames, access tokens, passwords, or machine-specific build directories to source files or documentation.

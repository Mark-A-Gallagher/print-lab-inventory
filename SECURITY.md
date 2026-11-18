# Security Policy

## Supported Versions

The following versions of the 3D Print Lab Inventory System are currently supported with security updates.

| Version | Supported |
|---|---|
| 1.0.x | Yes |
| Below 1.0 | No |

Support for future versions will be determined as new releases become available.

## Reporting a Vulnerability

If you discover a potential security vulnerability, please report it responsibly.

**Please do not publicly disclose security vulnerabilities through GitHub Issues.**

Instead, use GitHub's private vulnerability reporting feature if it is enabled for this repository.

When reporting a vulnerability, please include:

- A description of the vulnerability.
- Steps to reproduce the issue.
- The potential impact.
- Any relevant screenshots, logs, or proof-of-concept examples.

Please avoid including sensitive information, such as passwords, access tokens, or personal data, in your report.

## Response Process

As this is a personal development project, security reports will be reviewed as time permits.

After receiving a report, reasonable efforts will be made to:

1. Review and investigate the reported vulnerability.
2. Determine its severity and potential impact.
3. Develop and test an appropriate fix when necessary.
4. Release an update addressing the vulnerability.

Please allow time for the issue to be investigated before publicly disclosing it.

## Security Best Practices

When deploying or developing this application:

- Never commit passwords, API keys, or other secrets to the repository.
- Keep dependencies updated.
- Validate and sanitize user input.
- Use appropriate authentication and authorization controls.
- Avoid exposing sensitive database information through API responses.
- Use secure configuration practices when deploying outside a local development environment.


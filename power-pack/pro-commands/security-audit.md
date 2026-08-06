---
description: Run a security audit on code or architecture
argument-hint: [code, endpoint, or system to audit]
---
Perform a thorough security audit on the following. Check for:

1. **OWASP Top 10** — injection, broken auth, sensitive data exposure, XXE, broken access control, misconfiguration, XSS, insecure deserialization, vulnerable components, insufficient logging
2. **Authentication & authorization** — session handling, token management, privilege escalation paths
3. **Input validation** — every boundary where untrusted data enters
4. **Secrets management** — hardcoded keys, leaked credentials, insecure storage
5. **Dependencies** — known CVEs in third-party code
6. **Data protection** — encryption at rest and in transit, PII handling

For each finding: severity (critical/high/medium/low), exact location, proof-of-concept exploit scenario, and specific remediation with code.

Target: $ARGUMENTS

---
applyTo: "**/*.py"
---
# Python SSDLC Addendum

This addendum complements the Python/FastAPI Best Practices ruleset with Secure Software Development Lifecycle (SSDLC) guidance, ensuring security and quality are addressed at every stage of development.

---

## 1. Threat Modeling & Risk Assessment
- Perform threat modeling for new features, major changes, or integrations.
- Identify potential attack vectors (e.g., injection, XSS, CSRF, privilege escalation, data leakage).
- Document security assumptions and mitigations in design docs or issue trackers.
- Use tools like [OWASP Threat Dragon](mdc:https:/owasp.org/www-project-threat-dragon) or [Microsoft Threat Modeling Tool](mdc:https:/www.microsoft.com/en-us/securityengineering/sdl/threatmodeling) for structured analysis.

## 2. Security Testing
- Integrate static code analysis (e.g., [Bandit](mdc:https:/bandit.readthedocs.io), [PyLint security plugins](mdc:https:/pylint.pycqa.org)) into CI pipelines.
- Use dependency scanning tools (e.g., `pip-audit`, [Safety](mdc:https:/pyup.io/safety), [Dependabot](mdc:https:/github.com/dependabot)) to detect vulnerable packages.
- Perform regular vulnerability testing of deployed applications (e.g., [OWASP ZAP](mdc:https:/owasp.org/www-project-zap), [Nikto](mdc:https:/cirt.net/Nikto2)).
- Write and maintain security-focused tests (e.g., input validation, authentication flows, access control, SQL injection, SSRF).
- Review and test security headers (CORS, CSP, HSTS) in FastAPI middleware.

## 3. Incident Response & Monitoring
- Implement centralized error and security logging (e.g., ELK stack, Sentry, custom solutions).
- Monitor for suspicious activity (e.g., repeated failed logins, unusual API usage, privilege escalation attempts).
- Document incident response procedures:
  - How to report a security incident
  - Steps for investigation and remediation
  - Communication plan for affected users
- Regularly review and update incident response plans.

## 4. Data Lifecycle Management
- Define and document data retention and deletion policies for user data.
- Implement secure deletion of sensitive data (e.g., on user account deletion, GDPR/CCPA compliance).
- Ensure compliance with relevant privacy regulations (e.g., GDPR, CCPA, HIPAA).
- Review and document third-party data processors and their security practices.

## 5. Developer Security Training
- Encourage ongoing security training for all developers (e.g., OWASP Top 10, SANS Secure Coding, Python security courses).
- Share security updates, advisories, and lessons learned in team meetings or documentation.

---

**References:**  
- [OWASP Secure Software Development Lifecycle Project](mdc:https:/owasp.org/www-project-secure-software-development-life-cycle)  
- [OWASP Application Security Verification Standard (ASVS)](mdc:https:/owasp.org/www-project-application-security-verification-standard)  
- [NIST Secure Software Development Framework](mdc:https:/csrc.nist.gov/publications/detail/sp/800-218/final)  
- [OWASP Top 10](mdc:https:/owasp.org/www-project-top-ten)  
- [Bandit: Python Security Linter](mdc:https:/bandit.readthedocs.io)  
- [Safety: Python Dependency Checker](mdc:https:/pyup.io/safety)


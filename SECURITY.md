# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: **[your-email@example.com]**

You should receive a response within 48 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

Please include the following information:

- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

## Security Best Practices

### Environment Variables

**Never commit the `.env` file with real credentials!**

```bash
# Always use .env.example as template
cp .env.example .env

# Keep .env in .gitignore
echo ".env" >> .gitignore
```

### API Keys

- Use environment variables for all secrets
- Rotate API keys regularly
- Use different keys for dev/staging/production
- Monitor API usage for anomalies
- Revoke compromised keys immediately

### OpenAI API Key Security

If your OpenAI API key is compromised:

1. **Revoke immediately**: https://platform.openai.com/api-keys
2. **Create a new key**
3. **Update your `.env` file**
4. **Monitor usage**: Check for unauthorized requests
5. **Review billing**: Look for unexpected charges

### Docker Security

```bash
# Don't expose ports unnecessarily
# In docker-compose.yml, use internal networks

# Use secrets for production
docker secret create openai_key ./openai_key.txt

# Run containers as non-root user
# Already configured in Dockerfiles
```

### Rate Limiting

The application includes rate limiting:
- 10 requests per minute per user (default)
- Configurable via `RATE_LIMIT_PER_MINUTE`
- Helps prevent abuse and DoS attacks

### Input Validation

- Maximum message length: 5000 characters
- Maximum threads per user: 20
- Configurable via environment variables

### Database Security

**ClickHouse & Grafana:**
- Change default passwords in production
- Use strong passwords (min 16 characters)
- Enable HTTPS in production
- Restrict network access
- Regular backups

### Production Deployment

```bash
# Use secrets management
# Examples: AWS Secrets Manager, HashiCorp Vault

# Enable HTTPS/TLS
# Use reverse proxy (nginx, Traefik)

# Regular updates
docker compose pull
docker compose up -d

# Monitor logs
docker compose logs -f --tail=100
```

### Common Vulnerabilities

**We protect against:**
- SQL Injection (using parameterized queries)
- XSS (input sanitization)
- CSRF (API key authentication)
- DoS (rate limiting)
- Path traversal (input validation)

**Known Dependencies:**
- Regularly updated via `pip` and `pnpm`
- Automated security scanning recommended
- Monitor GitHub security alerts

## Security Updates

Security updates will be released as soon as possible after a vulnerability is confirmed.

- Subscribe to releases: https://github.com/YPT-ME/AIAgent/releases
- Watch for security advisories
- Update dependencies regularly

## Disclosure Policy

- Report received: Acknowledged within 48 hours
- Vulnerability confirmed: Within 5 business days
- Fix developed: Timeline varies by severity
- Fix released: Security patch version
- Public disclosure: After fix is released

## Acknowledgments

We appreciate security researchers who responsibly disclose vulnerabilities. Contributors will be acknowledged (with permission) in:

- Release notes
- CHANGELOG.md
- This SECURITY.md file

Thank you for helping keep RAG AI Agent secure! 🔒

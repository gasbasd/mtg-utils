---
description: Security best practices and sensitive data handling for mtg-utils
author: Simone Gasbarroni
version: 1.0
tags: ["security", "best-practices", "sensitive-data"]
---

# Security Practices

## Sensitive Data Handling

This document outlines security best practices for handling sensitive information in the mtg-utils project.

---

## Files to NEVER Process

### Environment Variables

- **DO NOT** read or process `.env` files
- **DO NOT** include environment variable contents in any output
- **ALWAYS** treat `.env` as a blacklisted pattern

### Configuration Files

- **DO NOT** read `config.json` or any configuration files containing credentials
- **NEVER** expose binder IDs, API keys, or tokens in logs or outputs
- **MUST** sanitize any configuration data before displaying

### Credentials and Tokens

- **NEVER** commit or store actual API tokens
- **NEVER** hardcode sensitive credentials in source code
- **ALWAYS** use environment variables or secure secret management

---

## Sensitive Data Patterns to Detect

The following patterns indicate sensitive data that should be redacted:

| Pattern | Example | Action |
|---------|---------|--------|
| `binder_id` | `abc123xyz` | Remove from output |
| API Key | `sk-...` | Redact completely |
| Token | `ghp_xxx` | Remove completely |
| Email | `user@example.com` | Consider anonymization |

---

## Best Practices

### In Code

```python
# ✅ GOOD - Use environment variables
import os

binder_id = os.environ.get("MOXFIELD_BINDER_ID")

# ❌ BAD - Hardcoded secrets
binder_id = "abc123xyz"  # NEVER DO THIS
```

### In Logs

```python
# ✅ GOOD - Sanitized logging
logger.info(f"Processing binder: ***{binder_id[-4:]}")

# ❌ BAD - Full credential exposure
logger.info(f"Processing binder: {binder_id}")
```

### In Configuration

```json
// ❌ BAD - Store real binder ID
{
  "binder_id": "real-binder-id-12345"
}

// ✅ GOOD - Use placeholder
{
  "binder_id": "YOUR_MOXFIELD_BINDER_ID_HERE"
}
```

---

## Security Checklist

Before committing code:

- [ ] No `.env` files included
- [ ] No hardcoded credentials
- [ ] No exposed API keys or tokens
- [ ] No sensitive user data in logs
- [ ] Configuration files use placeholders

---

## Emergency Response

If sensitive data is accidentally exposed:

1. **IMMEDIATELY** remove the data from the codebase
2. **IMMEDIATELY** change any exposed credentials
3. Review recent commits for additional exposure
4. Update `.gitignore` to prevent future occurrences

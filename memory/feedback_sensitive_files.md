---
name: feedback-sensitive-files
description: Never open .env or credentials files; use .env.example for formatting reference
metadata:
  type: feedback
---

Never read or open sensitive files: `.env`, `*.pem`, `*.key`, or any credentials files.

**Why:** User explicitly stated this. These files contain private keys and API secrets.

**How to apply:** If env var formatting is needed, read `.env.example` instead. If a .pem template is needed, create a blank one from scratch. Never use the Read tool on `.env` or credential files even if the user opens them in the IDE.

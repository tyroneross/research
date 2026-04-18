---
description: Inspect or set the source tier for a domain
argument-hint: <domain-or-url> [--tier T1|T2|T3|T4] [--reason "..."]
allowed-tools: Bash
---

Look up a domain's current tier, or set it manually.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" score $ARGUMENTS
```

Without `--tier`: reads the stored tier from `domain_scores`, applies deterministic rules if not cached, else reports unknown (flag for LLM judgment).

With `--tier`: sets a manual override. Manual entries are preserved across seed refreshes.

See `references/source_scoring.md` for tier definitions and rules.

---
description: Surface stale / review-due research entries ranked by a composite staleness score
argument-hint: [-n 20] [--topic <topic>]
allowed-tools: Bash
---

Compute a per-entry staleness score and list the top-N. Also writes `~/dev/research/review-due.md` for reference.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" review $ARGUMENTS
```

Staleness = `0.4 * months_since_reviewed * velocity_weight + 0.2 * source_version_drift + 0.2 * orphan + 0.2 * corroboration_loss`. See `references/lifecycle.md` for the full formula.

For each entry listed, the user can:
- Edit to refresh (updates `reviewed:` automatically on next save)
- `/research:archive <slug>` to retire
- `/research:compress <slug>` to shrink a bloated Raw section

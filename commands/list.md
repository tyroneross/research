---
description: List recent research entries
argument-hint: [-n 20] [--status evergreen|archived|...]
allowed-tools: Bash
---

Show recent entries:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" list $ARGUMENTS
```

Default is 20 most recently reviewed entries. Each line: date, confidence, slug, title.

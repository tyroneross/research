---
description: Persist a research entry markdown file into ~/research/ with symlinks and index rebuild
argument-hint: <path-to-entry.md>
allowed-tools: Bash
---

Persist the given entry file.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" save --file "$ARGUMENTS"
```

Report the canonical path, any project symlinks created, and the corroboration/confidence summary.

If no path was given, ask the user which file to save. Usually this command is invoked automatically by the research skill at the end of Phase 6 — manual invocation is for re-ingesting edits.

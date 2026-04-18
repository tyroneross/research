---
description: Rebuild ~/research/ markdown indexes and per-topic Maps of Content from the DB
allowed-tools: Bash
---

Rebuild `index.md`, `by-topic.md`, `by-project.md`, and per-topic MOCs at `~/research/indices/<topic>.md`. Also updates `inbound:` frontmatter on each entry by scanning for `[[slug]]` refs.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" index
```

Normally runs automatically via the PostToolUse hook. Invoke manually after bulk file edits or imports.

---
description: Rebuild ~/research/ markdown indexes, per-project RossLabs-Research.md files, and the master PORTFOLIO.md
allowed-tools: Bash
---

Rebuild every auto-generated index:

- `~/research/index.md` (chronological)
- `~/research/by-topic.md` (grouped by tag)
- `~/research/by-project.md` (grouped by project)
- `~/research/indices/<topic>.md` (per-topic Maps of Content)
- `<project>/RossLabs-Research.md` for every project that has at least one entry
- `~/research/PORTFOLIO.md` (master overview across all projects + cross-cutting)
- `inbound:` frontmatter on each entry (scans Notes for `[[slug]]` refs)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" index
```

Normally runs automatically via the PostToolUse hook and on every `/research:save`. Invoke manually after bulk file edits, after `/research:save --no-index`, or after re-organizing slugs.

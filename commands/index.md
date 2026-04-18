---
description: Rebuild ~/research/ markdown indexes, refresh managed symlinks, and re-scan all linked external projects
allowed-tools: Bash
---

Rebuild every auto-generated index and refresh every symlink:

- `~/research/index.md` (chronological)
- `~/research/by-topic.md` (grouped by tag)
- `~/research/by-project.md` (grouped by project)
- `~/research/indices/<topic>.md` (per-topic Maps of Content)
- `~/research/projects/<name>/<slug>.md` symlinks for every plugin-managed project (refreshed from current DB state)
- Every linked external project registered via `/research:link-project` (re-scanned: new files added, deleted files removed, summaries refreshed)
- `~/research/PORTFOLIO.md` (master overview with plugin-managed + linked external sections)
- `inbound:` frontmatter on each entry (scans Notes for `[[slug]]` refs)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" index
```

One call keeps the entire knowledge base current — both plugin-authored entries and linked external directories. Invoke manually after bulk file edits, after `/research:save --no-index`, or after re-organizing slugs.

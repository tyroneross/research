---
description: Persist a research entry markdown file into ~/research/ with project copy, symlink, and index rebuild
argument-hint: <path-to-entry.md> [--no-index]
allowed-tools: Bash
---

Persist the given entry file.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" save --file $ARGUMENTS
```

Writes the canonical entry to `~/research/topics/<top>/<slug>.md`. For each project listed in the entry's `projects:` frontmatter:

1. Writes a real-file copy to `<project>/research/<top>/<slug>.md` (visible, gets committed with the project).
2. Maintains a symlink at `<project>/research/.live/<slug>.md` pointing to the canonical entry (live-link convenience; `.live/` is added to the project's `.gitignore` automatically).
3. Regenerates `<project>/RossLabs-Research.md` (auto-generated index of all research linked to that project).
4. Regenerates `~/research/PORTFOLIO.md` (master corpus index).

Pass `--no-index` to skip the per-project and portfolio regen on this save (useful for batched edits — finish with `/research:index` to flush). The legacy `--skip-index` flag is preserved as an alias.

Migration: on first save after upgrade, any project with the legacy `<project>/.research/` directory is migrated to `<project>/research/.live/` automatically (idempotent).

Report the canonical path, real-file copy, symlink, project index, portfolio path, and the corroboration/confidence summary. If no path was given, ask the user which file to save. Usually this command is invoked automatically by the research skill at the end of Phase 6 — manual invocation is for re-ingesting edits.

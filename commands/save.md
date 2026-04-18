---
description: Persist a research entry markdown file into ~/research/ (canonical + optional project symlink + portfolio rebuild)
argument-hint: <path-to-entry.md> [--no-index] [--with-project-index]
allowed-tools: Bash
---

Persist the given entry file.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" save --file $ARGUMENTS
```

Writes the canonical entry to `~/research/topics/<top>/<slug>.md`. For each project listed in the entry's `projects:` frontmatter:

1. Maintains a symlink at `~/research/projects/<project-name>/<slug>.md` pointing to the canonical entry. No files are written into the project directory by default.
2. Regenerates `~/research/PORTFOLIO.md` (master corpus index, two sections: plugin-managed + linked external).

Pass `--no-index` to skip the portfolio regen on this save (useful for batched edits; finish with `/research:index` to flush). The legacy `--skip-index` flag is preserved as an alias.

Pass `--with-project-index` to additionally write `<project>/RossLabs-Research.md` inside the project directory. This is opt-in as of v0.3.1 — the default is to leave the project directory untouched. Use `/research:link-project` instead if you want to register a pre-existing research directory without modifying it.

Report the canonical path, the managed symlinks, the portfolio path, and the corroboration/confidence summary. If no path was given, ask the user which file to save. Usually this command is invoked automatically by the research skill at the end of Phase 6 — manual invocation is for re-ingesting edits.

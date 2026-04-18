---
description: Bulk-ingest existing markdown files into ~/research/ as draft entries
argument-hint: <path> [--project foo] [--topics a,b,c] [--inbox] [--save]
allowed-tools: Bash, Read, Write
---

Walk a file or directory of `.md` files and produce draft entries. The Python layer is purely deterministic (slug from filename, title from first H1, body wrapped into TL;DR/Notes/Raw skeleton). Anything semantic — picking topics, tagging sources by tier, pruning the body — is for you (the LLM) to do after seeing the drafts.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" ingest $ARGUMENTS
```

**Modes**

- No flags: print drafts to stdout, do not save. Inspect, fill in topics/tags, then call `/research:save` per file.
- `--save`: persist each draft via the normal save flow (creates canonical file, project copy, symlink, indexes).
- `--inbox`: copy raw files to `~/research/inbox/` without any drafting or DB write. Use this to "park" sources you want to review later.
- `--project foo`: auto-tag drafts with the named project (must match a directory under `~/Desktop/git-folder/`).
- `--topics a,b,c`: comma-separated topic list applied to every draft.

**Recommended LLM-assisted flow (slash command):**

1. Run `/research:ingest <path>` (no `--save`) to see the drafts.
2. For each draft, decide on topics, tags, source tiers, and slug refinements.
3. Edit the draft text in your head (or in a tmp file), then call `/research:save <tmp.md>` for that one entry.

For a fully automated dump (e.g. importing 50 old notes that you trust as-is), pass `--save` directly. Drafts are marked `confidence: inferred` and `status: fleeting` so the next `/research:review` pass surfaces them for proper synthesis.

---
description: Compress a research entry's Raw section — archive originals, prep for summary regeneration
argument-hint: <slug>
allowed-tools: Bash, Read, Edit
---

Compact an entry whose `## Raw` section has grown large.

1. The script moves the current Raw content to `~/dev/research/archive/raw/<slug>.md` (reversible).
2. The entry's Raw section is replaced with a placeholder + link to the archive.
3. The user (or you, in the next turn) should read the archived Raw and rewrite each source block as a 2–3 sentence summary with its URL and capture date preserved.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" compress $ARGUMENTS
```

After the script runs, edit the entry file to regenerate the summaries. TL;DR and Notes sections are left untouched.

See `references/lifecycle.md` for reversibility details.

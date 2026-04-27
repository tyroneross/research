---
description: Move a research entry to ~/dev/research/archive/ and leave a redirect stub
argument-hint: <slug>
allowed-tools: Bash
---

Archive an entry. The file moves to `~/dev/research/archive/<slug>.md`, and a 3-line redirect stub is left at the original path so `[[slug]]` backlinks from other entries still resolve.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" archive $ARGUMENTS
```

Never deletes. Reversible by manually moving the file back.

---
description: Retroactively symlink an existing research entry into the current (or given) project
argument-hint: <slug> [project-path]
allowed-tools: Bash
---

Link an existing entry into a project's `.research/` as a symlink + INDEX.md line.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" link $ARGUMENTS
```

If no project path is given, uses `cwd`. Updates the entry's frontmatter `projects:` list too so the DB stays consistent.

---
description: Rebuild SQLite from canonical topic markdown without rewriting entries
allowed-tools: Bash
---

Synchronize the SQLite index from the markdown files under `~/dev/research/topics/`.

Use this after migrations, manual file moves, or any case where the database and canonical markdown may have drifted.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" sync $ARGUMENTS
```

Useful options:

- `--prune-missing`: remove DB rows whose slug no longer appears under `topics/`
- `--no-index`: update SQLite only; skip markdown dashboard and symlink refresh

This command does not rewrite research entry files. It only reads canonical markdown, upserts SQLite rows, and then refreshes generated indexes/symlinks unless `--no-index` is passed.

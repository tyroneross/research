---
description: Bootstrap ~/research/ directory, SQLite FTS5 database, and seed domain scores
allowed-tools: Bash
---

Run the research plugin bootstrap:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" init
```

Report the bootstrap summary (paths created, domain scores seeded). If the user passes `--refresh-seeds` as an argument, include it — reseeds domain scores while preserving any manual overrides.

Arguments: $ARGUMENTS

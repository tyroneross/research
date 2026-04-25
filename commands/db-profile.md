---
description: Profile a SQLite database schema, tables, row counts, indexes, and foreign keys
argument-hint: <path-to-db> [-o profile.json]
allowed-tools: Bash
---

Profile a SQLite database before writing SQL or making database-backed claims.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" db-profile $ARGUMENTS
```

Use this to inspect tables, schemas, row counts, sample rows, indexes, and foreign keys. For joins, define expected cardinality before querying. Downgrade certainty when tables lack primary keys, joins are inferred, or important row counts are zero.


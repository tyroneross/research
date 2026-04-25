---
description: Profile a CSV/TSV/JSON table before quantitative research
argument-hint: <path> [-o profile.json]
allowed-tools: Bash
---

Profile a structured table before making quantitative claims.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" table-profile $ARGUMENTS
```

Use this before analysis on `.csv`, `.tsv`, `.json`, or `.jsonl` inputs. Report row count, columns, inferred types, blanks, numeric summaries, distinct counts, and sample rows. Treat profile warnings as certainty downgrades in the final research output.


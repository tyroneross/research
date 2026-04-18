---
description: Full-text search the research library with BM25 ranking
argument-hint: <query> [--tag X] [--topic Y] [--project Z] [-n 20]
allowed-tools: Bash
---

Search the research library. BM25-ranked across title, TL;DR, Notes, and Raw.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" search $ARGUMENTS
```

FTS5 query syntax: phrase `"chain of thought"`, boolean `cot AND reasoning`, prefix `agent*`, column filter `title: prompting`.

Present the top results with slug, title, confidence, and reviewed date. Offer to `cat` the most promising entry if the user wants the full content.

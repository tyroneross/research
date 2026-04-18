---
description: Suggest splits for top-level topics that have grown too large (read-only by default)
argument-hint: [--threshold N] [--apply --plan plan.json]
allowed-tools: Bash
---

Group existing entries by top-level topic and propose splits when a top-level exceeds the threshold (default 8). Pure deterministic counting; no LLM API calls.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" recategorize $ARGUMENTS
```

Default behavior is read-only. The script outputs structured cluster suggestions; review them, then build a JSON plan:

```json
{
  "renames": {
    "prompting.few-shot": "prompting.techniques.few-shot",
    "prompting.cot": "prompting.techniques.chain-of-thought"
  }
}
```

Apply the plan with:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" recategorize --apply --plan plan.json
```

Renames create the new entry, leave a redirect stub at the old path (so `[[old.slug]]` links still resolve), and update the DB. Indexes and the portfolio are rebuilt automatically.

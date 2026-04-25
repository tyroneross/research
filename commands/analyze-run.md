---
description: Run a generated quantitative analysis plan and write results/audit artifacts
argument-hint: --plan <analysis-plan.yaml> [--timeout 30] [--allow-modified-script]
allowed-tools: Bash
---

Run a generated quantitative analysis plan.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" analyze-run $ARGUMENTS
```

Outputs:

- `results.json`
- `audit.md`

Use the audit file to report quantitative findings with formula/query, validation status, limitations, and High / Medium / Low certainty.

By default, this refuses to run if `analysis.py` differs from the hash recorded in `analysis-plan.yaml`. If the script was intentionally edited for custom metrics, review it first, then pass `--allow-modified-script`.

---
description: Create a self-contained Python analysis plan and script for quantitative/database research
argument-hint: --input <path> --question "..."
allowed-tools: Bash
---

Create a quantitative analysis run directory.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" analyze-plan $ARGUMENTS
```

This profiles declared inputs and writes:

- `analysis-plan.yaml`
- `analysis-plan.json`
- one `*.profile.json` per input
- `analysis.py`

The generated script is stdlib-only and local by default. Do not install packages or download Python code unless the user explicitly approves the environment setup.

Next step:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" analyze-run --plan <analysis-plan.yaml>
```


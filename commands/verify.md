---
description: Run claim verification on a research entry (numeric / symbolic / citation / code)
argument-hint: <slug> [--atom <id>] [--dry-run]
allowed-tools: Bash, Read, Write
---

Verify the atomic claims in an entry.

**Prerequisite**: an atoms file must exist next to the entry at `<entry-dir>/<slug>.atoms.json` (JSON array of `{atom_id, type, claim, doi?, code?}`). If it doesn't exist, extract atoms first by reading the entry's Notes section and producing the atoms JSON — then re-run this command.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" verify $ARGUMENTS
```

Routes each atom to its verifier:
- `numeric` — parse numbers + units from claim, retrieve top-5 Raw chunks, compare
- `symbolic` — `sympy.simplify(lhs - rhs) == 0` (opt-in; inconclusive if sympy not installed)
- `citation` — OpenAlex lookup by DOI or title
- `code` — sandboxed Python subprocess (Docker if available)

Writes per-atom JSON artifacts to `~/dev/research/verifier-log/<slug>/`, updates entry frontmatter with `verification.*` counts, and recomputes `confidence` from corroboration + pass rate.

See `references/verification.md` for the full contract.

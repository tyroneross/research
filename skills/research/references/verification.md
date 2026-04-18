# Verification (v0.2+)

Deterministic verification of atomic claims. LLM extracts atoms; scripts verify.

## Pattern

```
Notes body → Extractor (LLM) → [atoms] → Router (code) → Verifier (code) → Report
```

Based on the FActScore / FacTool decompose-extract-retrieve-verify pattern, stripped to minimums.

## Atom types

```json
{
  "atom_id": "a1",
  "type": "numeric | symbolic | code | citation",
  "claim": "CoT improves GSM8K accuracy from 17.9% to 58.1%",
  "needs": ["benchmark_or_citation"],
  "source_refs": ["https://arxiv.org/abs/2201.11903"]
}
```

- **numeric** — a quantity, unit, comparison, or ratio.
- **symbolic** — an equation, closed-form, identity, or inequality.
- **code** — a Python snippet whose behavior is claimed.
- **citation** — an attribution ("Wei et al. 2022 introduced CoT") verifiable via OpenAlex.

## Routing (`research.py verify`)

| Type | Verifier | Dep |
|---|---|---|
| `numeric` | Regex-parse quantities + units, retrieve top-5 Raw chunks via FTS5, bootstrap CI via stdlib `statistics` + `random.choices`. | stdlib |
| `citation` | `urllib.request` → `api.openalex.org/works?filter=doi:<doi>` or `search=<title>`. Confirm existence + year. | stdlib |
| `symbolic` | `sympy.simplify(lhs - rhs) == 0`. Falls back to `inconclusive` if `sympy` not installed. | sympy (opt) |
| `code` | v0.3: `subprocess` + `tempfile` + resource limits (Docker if available). v0.2 marks `inconclusive`. | stdlib (+docker opt) |

## Verifier output

Each atom produces `~/research/verifier-log/<slug>/<atom_id>.json`:

```json
{
  "atom_id": "a1",
  "type": "numeric",
  "claim": "CoT improves GSM8K accuracy from 17.9% to 58.1%",
  "verdict": "passed | failed | inconclusive",
  "evidence": "Retrieved chunk #3 from arxiv.org excerpt states: '...58.1% on GSM8K...'",
  "artifact": "verifier-log/prompting.chain-of-thought/a1.stdout",
  "cmd": "python -c 'import statistics; ...'",
  "confidence": "✅ | ⚠️ | ❓",
  "timestamp": "2026-04-17T14:22:00Z"
}
```

## Entry-level rollup

After all atoms run, update entry frontmatter:

```yaml
verification:
  run: 2026-04-17T14:22:00Z
  atoms: 4
  passed: 3
  inconclusive: 1
  failed: 0
```

And combined with corroboration (see `source_scoring.md`), set the entry `confidence` field.

## Inline markers

When an atom fails or is inconclusive, `verify` appends a marker to the claim in Notes:

- Passed: no change.
- Inconclusive: `{claim: "...", atom_id: a1} ⚠️ unverified`
- Failed: `{claim: "...", atom_id: a1} ❌ verifier says X instead`

## Running

```bash
python research.py verify <slug>           # runs all atoms
python research.py verify <slug> --atom a1 # single atom (for debugging)
python research.py verify <slug> --dry-run # extract atoms, don't run verifiers
```

## What this is not

- Not a theorem prover. Lean/Coq are overkill for the claims we actually make.
- Not a full fact-checking service. Judgment calls (contested interpretations, qualitative claims) still need Claude.
- Not a safety sandbox for arbitrary code. v0.3 code execution assumes the user ran the research themselves; don't use it to verify untrusted third-party code.

## Extending

New atom types go in the router. Pattern:
1. Add to the `atoms` JSON schema the extractor prompt uses.
2. Add a case to `research.py verify`'s routing table.
3. Add a verifier function that returns `{verdict, evidence, artifact, confidence}`.

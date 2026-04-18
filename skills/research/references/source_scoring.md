# Source Scoring (v0.2+)

Deterministic, persisted tier assignment for every source URL. Same domain → same tier, across all research sessions.

## Tier definitions

Extends the T1–T4 framework in `credibility.md`:

| Tier | Examples | Auto-assignment signal |
|---|---|---|
| T1 | arxiv.org, official framework docs, WP:RSP "generally reliable", `.gov`/`.edu` research institutions, `github.com/<official-org>` | Seeded + deterministic rules |
| T2 | anthropic.com, openai.com, deepmind.com research, recognized eng blogs, well-cited papers | Seeded eng-blog allowlist |
| T3 | IEEE, ACM proceedings, reputable industry blogs, conference recordings | Rule-based partial matches |
| T4 | Reddit, Stack Overflow, Medium, Dev.to, Substack, personal blogs, SEO content, Iffy Index domains | Iffy CSV + social-media rules |

## Lookup pipeline

For a URL `https://<domain>/<path>`:

1. Parse eTLD+1 (`example.com` from `blog.example.com`, `github.io` from `vega.github.io` → **use `github.io` with `/<org>/` prefix check for github pages**).
2. Query `domain_scores` table: `SELECT tier FROM domain_scores WHERE domain = ?`. Hit → return.
3. Miss → apply rules (first match wins):
   - In Iffy Index CSV → T4.
   - In `data/domain-scores-seed.json` allowlist (T1/T2) → seeded tier.
   - `arxiv.org`, `doi.org` → T1.
   - `*.readthedocs.io`, `*.github.io/<org>` where org in official-org list → T1.
   - `.gov`, `.edu` → T1 (conservative; not all .edu are research, but close enough for personal use).
   - `github.com/<official-org>` → T1.
   - `github.com/<any-org>` → T2 (active repo) or T3 (stale) — check via API or default T2.
   - `reddit.com`, `stackoverflow.com`, `medium.com`, `dev.to`, `substack.com`, `news.ycombinator.com` → T3 (community) or T4 (per-topic judgment).
   - Anything else → **T4 provisional**, flagged for LLM review.
4. For the residue: Claude judges using `credibility.md` rationale, writes back to `domain_scores` with `set_by='llm'`. Same domain on next encounter hits the cache.

## `domain_scores` table

```sql
CREATE TABLE domain_scores (
  domain   TEXT PRIMARY KEY,
  tier     TEXT NOT NULL,       -- T1..T4
  reason   TEXT,                -- one-line rationale
  set_by   TEXT,                -- manual|seed|rule|llm
  set_date TEXT
);
```

Seeded from `data/domain-scores-seed.json` at `research.py init`.

## Per-source frontmatter

Each `sources[]` entry in an entry's frontmatter records:

```yaml
- url: https://arxiv.org/abs/2201.11903
  tier: T1              # from scoring pipeline
  domain: arxiv.org
  primary: true         # manually set: does this source originate the claim?
  doi: 10.48550/arXiv.2201.11903   # if applicable; confirmed via OpenAlex
  captured: 2026-04-17
```

`primary: true` means the source is where the claim originates (e.g., the paper that introduced a technique), not a secondary write-up.

## Corroboration count

`corroboration` (entry-level frontmatter) = count of **distinct** T1/T2 domains in `sources[]` that support the central claim.

- `corroboration: 2+` → `confidence: verified` (✅)
- `corroboration: 1` → `confidence: partial` (⚠️)
- `corroboration: 0` (all T3/T4) → `confidence: inferred` (❓)

Combined with v0.2 verification pass rate:
- `verified` also requires ≥80% of checked atoms passed.
- Otherwise downgrade one step.

## Maintenance

- **Seed refresh** — `data/iffy-domains.csv` and `domain-scores-seed.json` can be refreshed periodically from upstream (Iffy Index is CC BY 4.0). Re-run `research.py init --refresh-seeds` to merge new entries without overwriting manual scores.
- **Score override** — `python research.py score <domain> --tier T1 --reason "new policy"` updates `domain_scores` and sets `set_by='manual'`. Manual overrides never get clobbered by seed refresh.
- **Inspection** — `python research.py score <domain>` prints the stored tier and rationale.

## Why this works

- **Token efficiency**: LLM is called only on unknown domains. The first encounter pays, every subsequent one is free.
- **Reproducibility**: the same URL always scores the same; you can re-derive `corroboration` deterministically from `sources[]` → `domain_scores`.
- **Auditability**: `set_by` tells you whether a score was manual, seeded, rule-derived, or LLM-derived. Easy to re-review.

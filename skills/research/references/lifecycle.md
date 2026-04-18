# Lifecycle (v0.3+)

Staleness detection, archival, and compression. Keeps the knowledge base useful over years without losing anything.

## Staleness scalar

Computed per entry by `research.py review`:

```
staleness = 0.4 * months_since_reviewed * velocity_weight
          + 0.2 * source_version_drift
          + 0.2 * (inbound_count == 0 ? 1 : 0)
          + 0.2 * corroboration_loss
```

- `velocity_weight`:
  - `high` = 2.0  (fast-moving fields: prompting, model deployment, AI tooling)
  - `medium` = 1.0 (established tech: databases, web frameworks)
  - `low` = 0.4   (fundamentals: CS theory, math, design principles)
- `source_version_drift`: 1 if the stored `source_version` frontmatter no longer matches a fresh fetch, else 0. Requires a periodic rescrape job (can be manual).
- `inbound_count`: from `inbound:` frontmatter, auto-maintained by `research.py index`. 0 inbound = orphan candidate.
- `corroboration_loss`: 1 if any source domain has been downgraded in `domain_scores` since `captured`, else 0.

Threshold: entries with `staleness > 3.0` land in `~/research/review-due.md` top-N.

## Review surface

```bash
python research.py review          # print top-20 + write review-due.md
python research.py review --topic prompting
python research.py review --json   # for piping
```

Output: entry slug, title, staleness score, breakdown of contributing factors, `reviewed:` date.

Decide per entry:
- **Refresh**: edit the file; `reviewed:` auto-updates on save.
- **Archive**: `research.py archive <slug>`.
- **Compress**: `research.py compress <slug>` (see below).
- **Leave alone**: do nothing; will re-surface next review.

## Archival

```bash
python research.py archive prompting.chain-of-thought
```

Effects:
1. Move `~/research/topics/prompting/prompting.chain-of-thought.md` → `~/research/archive/prompting.chain-of-thought.md`.
2. Write a 3-line redirect stub at the original path:
   ```markdown
   ---
   status: archived
   redirect: ../../archive/prompting.chain-of-thought.md
   archived: 2026-04-17
   ---
   Archived. See [[archive/prompting.chain-of-thought]].
   ```
3. Update DB entry: `status = 'archived'`.
4. Rebuild indexes via hook.

The stub preserves `[[prompting.chain-of-thought]]` backlinks from other entries — they still resolve, just route through the redirect.

**Never** `rm` an entry file. Inbound links, historical context, and verification artifacts all assume the content is recoverable.

## Compression

When a Raw section grows large (many sources, long excerpts):

```bash
python research.py compress prompting.chain-of-thought
```

Effects:
1. Copy pre-compression state to `~/research/archive/raw/prompting.chain-of-thought.md` (full original Raw content).
2. Claude regenerates:
   - `## TL;DR` from current Notes (re-extractive, ≤150 words).
   - Each `### <url>` block in Raw → 2–3 sentence summary with a link back to the archive copy.
3. Notes section is untouched.
4. Update `reviewed:` to today.
5. Write a compression log entry to `~/research/verifier-log/<slug>/compress-<timestamp>.json` with byte counts before/after.

**Reversible**: restoring the entry is a straight copy from `archive/raw/<slug>.md` back into the entry file's Raw section.

## Topic velocity defaults

Stored in `data/topic-velocity.yaml` (shipped with plugin, user-editable):

```yaml
prompting: high
model-deployment: high
llm-evals: high
db: medium
web-frameworks: medium
design: medium
algorithms: low
math: low
cs-theory: low
```

When creating an entry, `research.py save` looks up the top-level topic in this file and assigns `topic_velocity` automatically. Users can override via frontmatter.

## Periodic automation

Optional — set up via the existing `schedule` skill:

```bash
# Weekly review surfacing
0 9 * * 1  python ~/.claude/plugins/research/research.py review --slack-me
```

(The `--slack-me` flag is a placeholder; wire to any notification you prefer.)

## What compression does NOT do

- Does not delete links.
- Does not touch Notes body — the bolded key passages survive.
- Does not re-verify claims. If you want fresh verification post-compression, run `research.py verify` again.
- Does not change slugs, filenames, or frontmatter structure — only the TL;DR text and Raw section summaries.

# Persistence (Phase 6)

How research gets saved into the central knowledge base at `~/research/`.

## Layout

```
~/research/
  .db.sqlite3                   # FTS5 index, domain scores, verifier log
  README.md                     # auto-bootstrapped
  index.md                      # AUTO: chronological list of all entries
  by-topic.md                   # AUTO: grouped by tag
  by-project.md                 # AUTO: grouped by project
  review-due.md                 # AUTO: staleness-ranked
  PORTFOLIO.md                  # AUTO (v0.3): master corpus index, by project + cross-cutting
  topics/
    <top-level>/
      <slug>.md                 # canonical entries
  indices/
    <top-level>.md              # AUTO: Map of Content per top-level topic
  archive/
    <slug>.md                   # moved, never deleted
    raw/<slug>.md               # pre-compress Raw excerpts
  verifier-log/<slug>/<atom>.json   # per-claim verification artifacts (v0.2+)
  inbox/                        # unrefined fleeting notes; populated by /research:ingest --inbox
```

Per project (when entry frontmatter has `projects: [foo]` and `~/Desktop/git-folder/foo/` exists):

```
<project>/
  research/
    <top>/<slug>.md             # AUTO (v0.3): real-file copy, visible, committed
    .live/<slug>.md             # AUTO: symlink to ~/research/topics/<top>/<slug>.md (gitignored)
  RossLabs-Research.md          # AUTO (v0.3): per-project index of all linked entries
  .gitignore                    # auto-amended to include `research/.live/`
```

## Slug rules

- Dendron-style dot-hierarchy: `<top-level>.<sub>.<specific>`. Examples:
  - `prompting.chain-of-thought`
  - `prompting.techniques.few-shot`
  - `db.postgres.pgvector`
  - `design.calm-precision.forms`
- Lowercase kebab-case segments. No spaces.
- Top-level = the folder under `~/research/topics/`. Subsequent segments are purely in the filename.
- Collision handling: if the exact slug exists with today's date, append `-v2`, `-v3`, ...

## Frontmatter schema

```yaml
---
slug: prompting.chain-of-thought        # required, unique, matches filename
title: "Chain-of-Thought prompting"     # required
topics: [prompting, reasoning]          # required, ≥1
projects: []                            # [] if cross-cutting
status: evergreen                       # fleeting | literature | evergreen | archived
workflow: general                       # general | collection | synthesis
created: 2026-04-17                     # required, ISO date
reviewed: 2026-04-17                    # required, ISO date, updated on each edit
topic_velocity: medium                  # low | medium | high — staleness weight
tags: [cot, reasoning, few-shot]
confidence: verified                    # verified | partial | inferred
corroboration: 2                        # distinct T1/T2 domains agreeing
sources:
  - url: https://arxiv.org/abs/2201.11903
    tier: T1
    domain: arxiv.org
    primary: true
    doi: 10.48550/arXiv.2201.11903
    captured: 2026-04-17
  - url: https://www.anthropic.com/research/...
    tier: T2
    domain: anthropic.com
    primary: false
    captured: 2026-04-17
related: []                             # slugs of related entries
inbound: []                             # auto-maintained by research.py index
verification:                           # populated by research.py verify (v0.2+)
  run: null
  atoms: 0
  passed: 0
  inconclusive: 0
  failed: 0
---
```

**Required fields:** slug, title, topics, projects, status, created, reviewed, sources. Everything else defaults.

## Extraction — which tool for which source

Phase 2-3 research populates the `## Raw` section. Pick the right extractor per source type:

| Source | Tool | Why |
|---|---|---|
| HTML page (URL) | `WebFetch` | Built-in, returns markdown |
| Short PDF (≤10 pages, simple text) | `Read` with `pages` param | Built-in, fast, no deps |
| Any PDF (long, tables, scanned text) | `/research:extract <path>` | Routes to `@tyroneross/omniparse` |
| Excel (`.xlsx`, `.xls`, `.csv`, `.tsv`, `.ods`, `.xlsb`) | `/research:extract <path>` | Omniparse; `--sheet NAME` to pick one |
| PowerPoint (`.pptx`) | `/research:extract <path>` | Omniparse; `--no-notes` to strip speaker notes |
| Python source (`.py`) | `/research:extract <path>` | Omniparse — AST-level structured markdown |
| Whole docs directory | `/research:extract <dir> -r` | Omniparse recursive walk |
| Markdown / plain text / JSON / YAML | `Read` | Stdlib covers it; `/research:extract` rejects these |

### Omniparse

`/research:extract` routes everything through `@tyroneross/omniparse` — a user-authored Node.js CLI (FSL-1.1-MIT) that ships **vendored** inside this plugin at `vendor/omniparse/dist/bin/omniparse.js`. The vendored build is self-contained: all runtime deps (xlsx, sax, p-limit) are inlined, so no `npm install` is needed. Only `node >= 18` must be on PATH. No external Python extraction libraries are used. PDF handling is basic text extraction (no table or formula recognition). If academic PDF fidelity ever blocks real work, the right fix is to extend Omniparse rather than add another dependency.

Omniparse binary resolution (in order):
1. `omniparse` on `PATH` (allows a user-installed global override).
2. Vendored self-contained build at `<plugin-root>/vendor/omniparse/dist/bin/omniparse.js` invoked via `node`.

If neither resolves, the command explains that the vendored copy is missing or `node` isn't installed, and points at `vendor/omniparse/BUILD.md` for re-vendoring instructions.

### Caching

Every successful extract is cached at `~/research/.extract-cache/<sha256>-<flags>.md`. The cache key combines the file's SHA-256 (or a directory-listing hash for directories) with the active flag signature (`-f`, `-r`, `--sheet`, `--no-notes`). Re-reading the same file with the same flags is instant. Use `--no-cache` to force re-extract. Safe to delete the cache dir at any time.

Guiding rule: **non-LLM parsers do extraction, Claude does synthesis.** Paste the markdown verbatim into `## Raw`, under a heading with the source path + capture date. The verifier chunks this later.

## Three-layer template

```markdown
## TL;DR

≤150 words. Standalone. Extractive: reuse bolded phrases from Notes verbatim. Lead with the answer.

## Notes

Body. **Bold key passages** (Forte's progressive summarization). Use `[[prompting.techniques.few-shot]]` for backlinks. Cite inline as `[T1: https://arxiv.org/...]`.

Wrap numeric/code/symbolic claims so the verifier can find them:
`{claim: "CoT improves GSM8K accuracy from 17.9% to 58.1%", atom_id: a1}`

## Raw

Verbatim extracts. One section per source:

### https://arxiv.org/abs/2201.11903 (captured 2026-04-17)
[Paste the `WebFetch` markdown output verbatim, trimmed to relevant portions.]

### https://www.anthropic.com/research/... (captured 2026-04-17)
[Paste `WebFetch` output.]
```

The Raw layer is what FTS5 indexes for retrieval and what the v0.2 verifier chunks.

## Project association (v0.3)

When `projects[]` is non-empty and a project directory exists at `~/Desktop/git-folder/<name>/`, `research.py save` does three things:

1. **Real-file copy**: writes `<project>/research/<top>/<slug>.md` with the full canonical content (frontmatter + body). Visible, gets committed with the project. Travels with the repo.
2. **Live symlink**: creates `<project>/research/.live/<slug>.md` → `~/research/topics/<top>/<slug>.md`. Lets you follow updates from the central corpus. Auto-added to project `.gitignore` if one exists.
3. **Project index**: regenerates `<project>/RossLabs-Research.md` — auto-generated, do-not-edit list grouped by top-level topic, with title, link, last reviewed, confidence, and a 1-line summary extracted from each entry's TL;DR.

Master view: `~/research/PORTFOLIO.md` is regenerated alongside, summarizing every project (entries / topics / paths) plus cross-cutting topics.

`--no-index` defers the per-project and portfolio regen on a single save (useful for batches). `/research:index` flushes everything.

**Migration from v0.2**: any project with the old `<project>/.research/` directory is silently migrated to `<project>/research/.live/` on first save. Idempotent.

## Update vs create

- Same `slug` + same `created` date → update (overwrite entry file, rewrite frontmatter).
- Same `slug` + different `created` → append `-v2` suffix.
- Always update `reviewed: <today>` on any edit.

## Retroactive linking

If you realize later that research `prompting.chain-of-thought` is relevant to a project:

1. Edit frontmatter to add the project: `projects: [atomize-ai]`.
2. Run `python research.py link prompting.chain-of-thought ~/Desktop/git-folder/atomize-ai`.
3. Script creates the symlink and appends to that project's `INDEX.md`.

## Archival (v0.3 preview)

`python research.py archive <slug>` moves the file to `archive/<slug>.md`, sets `status: archived`, and leaves a 3-line redirect stub at the original path so `[[...]]` links from other entries still resolve. Never `rm`.

## Bootstrap

On any invocation, if `~/research/` is missing, `research.py` creates the full layout, the SQLite DB with FTS5 tables, and seeds `domain_scores` from `data/domain-scores-seed.json` (v0.2+).

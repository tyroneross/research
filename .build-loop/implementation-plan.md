# Research Plugin Implementation Plan

## Recommendation

Re-architect the plugin so that **Obsidian is the content system of record** and **SQLite is a derived local index and metadata layer**. Do not keep `~/research` as the primary long-term corpus if the user's actual knowledge workflow lives in `/Users/tyroneross/Documents/Obsidian Vault`.

Constraint update:

- Obsidian ingest/sync will be built separately and is out of scope for this plugin plan.
- This plugin should focus on indexing, search, metadata, and workflow behavior over an already-available markdown corpus.

That gives the cleanest separation:

- **Markdown lives in Obsidian**
- **SQLite accelerates search, filtering, verification state, source scoring, and review queues**
- **The plugin becomes an ingestion, indexing, and workflow layer instead of a parallel note store**

---

## 1. Current Architecture

### 1.1 Storage

- Canonical notes are written to `~/research/topics/<top>/<slug>.md`.
- Secondary generated artifacts live beside them:
  - `~/research/index.md`
  - `~/research/by-topic.md`
  - `~/research/by-project.md`
  - `~/research/review-due.md`
  - `~/research/PORTFOLIO.md`
  - `~/research/archive/`
  - `~/research/projects/<project>/...` symlinks

### 1.2 Index

- SQLite database lives at `~/research/.db.sqlite3`.
- It stores:
  - `entries`
  - `entries_fts`
  - `domain_scores`
- FTS5 is the current search engine.

### 1.3 Workflow Role of SQLite

SQLite is not a passive implementation detail. It is used directly by the product for:

1. Save/upsert of entry metadata and section bodies.
2. Full-text search with BM25 ranking.
3. Recent-entry listing.
4. Domain tier scoring cache and overrides.
5. Verification state rollups.
6. Review/staleness ranking inputs.
7. Index regeneration support.

### 1.4 Project Association

- Plugin-authored notes: `projects:` frontmatter creates central symlinks under `~/research/projects/`.
- External project research: `link-project` registers external markdown directories and creates symlinks under the same central tree.

### 1.5 Architectural Tension

The plugin currently assumes the note corpus should live in `~/research/`.

Your stated preference is different:

- research reports should be ingested into `/Users/tyroneross/Documents/Obsidian Vault`
- SQL should sit over that corpus

That means the current design is directionally useful, but the storage boundary is wrong for your preferred operating model.

---

## 2. Dependency Audit

## 2.1 Dependency Classification

| Dependency | Status | Source | Where Used | Notes |
|---|---|---|---|---|
| Python 3 | Required | Environment | Entire plugin | Primary runtime for `research.py` |
| `sqlite3` stdlib module | Required | Bundled with Python stdlib | `research.py` schema, search, save, review, score, verify | Required for current architecture; no separate package install |
| SQLite FTS5 support in Python's SQLite build | Required for search | Environment/runtime capability | `entries_fts` virtual table | If absent, search architecture fails |
| PyYAML | Required | `requirements.txt` | frontmatter parse/dump | Only declared required Python package |
| `sympy` | Optional | Environment | symbolic verification only | Graceful fallback when absent |
| Node.js >= 18 | Optional in general; required for extraction | Environment | Omniparse invocation | Needed only for `/research:extract` |
| Vendored Omniparse bundle | Optional feature dependency | Bundled in plugin | PDF/Excel/PPTX/Python/directory extraction | Ships in `vendor/omniparse/` |
| `jq` | Optional convenience | Environment | hook parsing fallback | Hook falls back to Python if absent |

## 2.2 Is SQLite Needed Or Optional?

### Current architecture

SQLite is **required** for the product as currently written.

Reason:

- search depends on FTS5
- save depends on DB upsert
- list depends on DB reads
- score depends on `domain_scores`
- review depends on DB metadata
- verify rollup depends on DB state sync

It is **not** just a convenience for local install. It is a core part of the current design.

### Future architecture

SQLite should remain **required as the derived index**, but **not as the source of truth**.

That is the distinction to preserve:

- **Markdown source**: Obsidian vault
- **Operational index**: SQLite

This keeps the plugin aligned with your actual note system while preserving fast local search and workflow features.

## 2.3 What Is Bundled In The Plugin vs External?

### Bundled in plugin

- `research.py`
- command markdown files
- research skill
- hooks
- domain seed data
- vendored Omniparse distribution

### External / environmental

- Python runtime
- PyYAML install
- optional SymPy install
- Node runtime for extraction
- filesystem locations:
  - current: `~/research`
  - desired: `/Users/tyroneross/Documents/Obsidian Vault`

---

## 3. Target Architecture

## 3.1 Source of Truth

Move to:

- `/Users/tyroneross/Documents/Obsidian Vault`

Recommended vault structure:

```text
/Users/tyroneross/Documents/Obsidian Vault/
  Research/
    topics/
    projects/
    inbox/
    archive/
    generated/
```

Suggested rule:

- human-authored and agent-authored markdown notes live in the vault
- generated dashboard files may also live in the vault if you want Obsidian-native navigation
- SQLite DB can live outside the vault or under a hidden subpath

Recommended DB location:

- `/Users/tyroneross/Documents/Obsidian Vault/.research-index/research.db`

Reason:

- keeps index local to the vault
- keeps content portable
- avoids mixed content/index semantics in the visible note tree

## 3.2 SQLite Role in Target State

SQLite should index:

- note path
- slug
- title
- topics
- projects
- tags
- status
- confidence
- reviewed date
- verification summary
- note body sections
- backlinks/inbound relations
- source metadata

SQLite should not be treated as the canonical copy of the markdown content. It should mirror and accelerate it.

## 3.3 Search Model

### Primary search surface

- Obsidian vault markdown corpus

### Derived search/index layer

- SQLite FTS5 for:
  - CLI search
  - plugin search
  - review queues
  - structured filters
  - metadata joins

### Design principle

If SQLite is deleted, the corpus still exists.

If the vault is deleted, the product is broken.

That is the right dependency direction.

---

## 4. Planned Product Changes

## Milestone 1: Separate Content Store From Index

### Goal

Stop assuming `~/research` is the canonical corpus.

### Changes

1. Introduce a config layer for:
   - `RESEARCH_CONTENT_DIR`
   - `RESEARCH_INDEX_DIR`
2. Replace the current `BASE_DIR` single-root assumption with:
   - content root
   - index root
3. Keep current env vars as compatibility aliases.

### Deliverable

- plugin can point markdown storage at Obsidian vault
- SQLite can live in a separate hidden index directory

### Risk

- path assumptions in save/index/link-project/archive need careful refactor

---

## Milestone 2: Make Vault Markdown the Canonical Write Target

### Goal

Persist new research entries directly into the Obsidian vault.

### Changes

1. Change `save` so canonical markdown writes target vault paths.
2. Update archive/compress/recategorize to operate on vault files.
3. Keep symlink/project behavior only if it still adds value after the vault shift.

### Recommendation

Once Obsidian is the source corpus, project-specific symlink trees probably become less important than:

- frontmatter-based project tags
- Obsidian properties
- generated project index notes

### Deliverable

- new research reports land in Obsidian automatically

Note:

- Defer this milestone until the separate ingest/sync system is defined.
- For now, the plugin should not take ownership of Obsidian ingestion automation.

---

## Milestone 3: Rebuild SQLite As A Derived Index

### Goal

Turn SQLite into a reindexable mirror of the vault.

### Changes

1. Add full reindex command over the vault.
2. Add incremental reindex by changed file path.
3. Make `save` update markdown first, then reindex the affected note.
4. Add integrity command:
   - detect DB rows for missing files
   - detect vault notes missing DB entries

### Deliverable

- DB can be dropped and rebuilt from vault contents

### Success condition

- no business-critical state exists only in SQLite

---

## Milestone 4: Improve Search and Metadata Filtering

### Goal

Keep SQLite because it materially improves local search and workflow.

### Changes

1. Add weighted FTS ranking.
2. Add snippets/highlighted search results.
3. Add structured metadata indexes instead of JSON `LIKE` filters.
4. Index all linked or imported Obsidian research content, not just plugin-authored entries.

### Deliverable

- fast vault-wide search through SQL

---

## Milestone 5: Obsidian-Native Navigation Layer

### Goal

Make the vault pleasant to browse without requiring the CLI.

### Changes

1. Standardize frontmatter/properties for Obsidian:
   - slug
   - title
   - topics
   - projects
   - tags
   - status
   - confidence
   - reviewed
2. Generate index notes:
   - by topic
   - by project
   - review queue
   - master portfolio
3. Preserve backlinks via wiki-links.

### Deliverable

- notes are first-class inside Obsidian
- SQL is additive, not a competing system

---

## Milestone 6: Periodic Obsidian Ingestion Workflow

Status: deferred to separate system

### Goal

Support your preferred habit: periodically move research outputs into the vault, then reindex SQL over it.

### Recommended workflow

1. Research output is generated in a staging area.
2. Periodic ingest command copies or moves reports into Obsidian vault structure.
3. Reindex job updates SQLite.
4. Generated dashboards refresh.

### Commands to add

- `research.py ingest-vault --source <dir>`
- `research.py reindex-vault`
- `research.py sync-vault`

### Deliverable

- periodic batch ingestion to Obsidian
- deterministic SQL refresh after ingest

Implementation note:

- This milestone is intentionally out of scope for the current plugin workstream.
- The plugin may later consume the resulting vault, but should not implement the ingestion/sync mechanism itself.

---

## 5. Implementation Sequence

## Phase A: Foundation

1. Add config split: content root vs index root.
2. Introduce `VaultAdapter` / path abstraction.
3. Keep current `~/research` behavior as default compatibility mode.

## Phase B: Migration Mode

1. Add Obsidian vault path support.
2. Add full reindex-from-vault.
3. Add migration tool:
   - move or copy `~/research/topics/**` into vault
   - rebuild DB from vault

## Phase C: Search Upgrade

1. Improve FTS result quality.
2. Add structured metadata indexes.
3. Add linked-content full-text indexing.

## Phase D: Workflow Upgrade

1. Add periodic ingest command.
2. Add Obsidian-friendly generated notes.
3. Add validation/lint before save.

---

## 6. Explicit Decisions

## Decision 1: Keep SQLite

Yes. Keep it.

But redefine its role:

- **required derived index**
- **not canonical storage**

## Decision 2: Stop Treating `~/research` As The Main Knowledge Base

Yes, if your real usage is Obsidian.

`~/research` should either:

- become compatibility mode, or
- be deprecated in favor of vault-backed storage

## Decision 3: Prefer Ingestion Over Duplication

Yes.

The plugin should ingest into the vault and index that vault, not maintain two independent long-term corpora.

Revision:

- The ingest/sync part will be handled by a separate system.
- This plugin should prepare to index and operate over that resulting corpus, not build the ingest pipeline itself.

---

## 7. Open Questions To Resolve Before Building

1. Should generated dashboard notes also live inside the Obsidian vault, or only the canonical research notes?
2. Should periodic ingestion be copy-based or move-based?
3. Do you want the plugin to write directly into the vault on every save, or keep a staging area and batch-ingest later?
4. Should project association continue as symlink trees, or be replaced with Obsidian properties plus generated project indexes?

---

## 8. Recommended Next Build Chunk

Start with the smallest architectural step that unlocks the rest:

### Chunk 1

Introduce split roots:

- `RESEARCH_CONTENT_DIR`
- `RESEARCH_INDEX_DIR`

Then refactor save/search/index to use those abstractions without changing behavior.

Why first:

- low conceptual risk
- preserves current behavior
- makes Obsidian migration possible without a full rewrite

### Chunk 2

Add `reindex-vault` against `/Users/tyroneross/Documents/Obsidian Vault`.

Why second:

- proves the future architecture
- lets SQL sit over the vault before changing write semantics

### Chunk 3

Switch canonical write target from `~/research` to Obsidian vault once reindex is stable.

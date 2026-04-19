# Next Chunks

## Chunk 1: Split Content Root And Index Root

Status: completed on 2026-04-19

### Goal

Separate canonical markdown storage from derived index/state storage without changing the default behavior.

### Scope

- Add `RESEARCH_CONTENT_DIR`
- Add `RESEARCH_INDEX_DIR`
- Keep `RESEARCH_BASE_DIR` as a compatibility alias
- Route:
  - markdown corpus and generated markdown views to content root
  - SQLite DB, linked-project registry, verifier logs, and extract cache to index root
- Update hook path detection for configurable content root
- Document the new path model

### Acceptance

- default install still behaves like `~/research`
- plugin can initialize with different content and index roots
- save/search/index continue to work against the refactored path helpers

## Chunk 2: Reindex External Vault

Status: next

### Goal

Allow the plugin to build its SQL index from an external markdown corpus that already exists, without owning ingestion or sync into that corpus.

### Scope

- Add a vault reindex command
- Walk the configured content root for canonical research notes
- Rebuild SQLite entirely from markdown files
- Add integrity checks for missing files / missing rows
- Do not implement ingest, sync, or scheduled import into Obsidian as part of this chunk

### Acceptance

- DB can be deleted and rebuilt from markdown
- reindex works against `/Users/tyroneross/Documents/Obsidian Vault` once content layout is chosen

## Chunk 3: Vault-Backed Canonical Writes

Status: pending

### Goal

Make the Obsidian corpus the primary write target.

### Scope

- Write new canonical research notes into the configured vault
- Update archive/compress/recategorize against vault-backed paths
- Align generated views and hooks with the new canonical path

### Acceptance

- new reports land in the vault
- reindex is incremental after save/edit

## Chunk 4: Search And Metadata Upgrade

Status: pending

### Goal

Improve local search quality now that SQL is clearly the derived index.

### Scope

- weighted ranking
- snippets/highlights
- structured metadata indexes instead of JSON `LIKE`
- full-text coverage for externally linked content

### Acceptance

- higher quality CLI search
- faster metadata filters

## Chunk 5: Periodic Obsidian Ingest Workflow

Status: deferred to separate system

### Goal

Support periodic batch ingest into the vault and SQL refresh over that corpus.

### Scope

- ingest/sync commands
- optional staging area
- generated dashboards and review queues refreshed after ingest

### Acceptance

- periodic Obsidian ingestion is first-class
- plugin no longer assumes it owns the only long-term corpus

# Architecture And Dependency Audit

## Executive Summary

The current plugin is **not** just a markdown writer with optional local search. Its current architecture depends on SQLite as an operational subsystem. However, SQLite is required because of the way the plugin is currently designed, not because SQLite must be the long-term source of truth.

For your preferred future state, the correct model is:

- **Obsidian Vault = canonical content**
- **SQLite = derived local index**

That keeps the plugin useful for fast search and workflow features without forcing a second note system.

---

## 1. Current Runtime Architecture

## 1.1 Main runtime

- `research.py`
- Python CLI entrypoint
- local filesystem writes
- SQLite-backed metadata and FTS

## 1.2 Main data paths

- Current canonical content root:
  - `~/research`
- Current DB:
  - `~/research/.db.sqlite3`
- Current project association:
  - `~/research/projects/<name>/...`

## 1.3 Current plugin surfaces

- Claude plugin:
  - `.claude-plugin/plugin.json`
- Codex plugin:
  - `.codex-plugin/plugin.json`
- Commands:
  - `commands/*.md`
- Hooks:
  - `hooks/hooks.json`
- Skill:
  - `skills/research/SKILL.md`

---

## 2. Dependency Matrix

| Dependency | Required Now | Required Later | Bundled In Plugin | Notes |
|---|---:|---:|---:|---|
| Python runtime | Yes | Yes | No | Core execution runtime |
| `sqlite3` stdlib | Yes | Yes | Via Python stdlib | No separate install, but operationally required |
| SQLite FTS5 support | Yes | Yes | Via Python's SQLite build | Required for current and planned local search |
| PyYAML | Yes | Yes | No | Frontmatter parsing |
| SymPy | No | No | No | Optional symbolic verification |
| Node.js | No | No | No | Only needed for extract workflow |
| Vendored Omniparse | No | No | Yes | Optional extraction feature |
| jq | No | No | No | Hook convenience only |

---

## 3. Where SQLite Is Used Today

SQLite is used in these command families:

### 3.1 Persistence

- `save`
- metadata upsert into `entries`

### 3.2 Search

- `search`
- `entries_fts MATCH ?`
- BM25 ranking

### 3.3 Listing and filters

- `list`
- status-based entry retrieval

### 3.4 Domain/source scoring

- `score`
- `domain_scores` cache and overrides

### 3.5 Verification

- verifier state rollup back into indexed metadata

### 3.6 Review lifecycle

- `review`
- ranking stale entries from DB-backed metadata

### 3.7 Index maintenance

- portfolio rebuild input
- project mapping refresh
- backlink/inbound metadata sync

Conclusion:

SQLite is currently a **core subsystem**, not an optional add-on.

---

## 4. What Is Truly Optional

These are optional today:

### 4.1 SymPy

- Only affects symbolic verification.
- Plugin degrades gracefully without it.

### 4.2 Node.js and Omniparse

- Only affects `/research:extract`.
- Core markdown save/search/index workflows still work without it.

### 4.3 Hook helper tools

- `jq` is optional.

---

## 5. What Is Bundled vs External

## Bundled

- plugin manifests
- command docs
- hooks
- skill docs
- domain seed data
- vendored Omniparse bundle

## External

- Python interpreter
- PyYAML package
- optional SymPy package
- optional Node runtime
- storage directories outside the repo

---

## 6. Architectural Recommendation

## Keep

- SQLite
- FTS5
- local-first indexing
- deterministic domain scoring
- verification logs
- generated review and portfolio outputs

## Change

- canonical storage root
- indexing direction
- note-system ownership model

## Recommended ownership model

### Current

- plugin owns canonical markdown in `~/research`

### Recommended

- Obsidian owns canonical markdown
- plugin indexes and augments it

This is the cleaner system because it matches your actual knowledge workflow.

---

## 7. Migration Principle

After the refactor:

- deleting SQLite should be recoverable by reindexing the vault
- deleting the vault should not be recoverable from SQLite alone

That is the correct source-of-truth relationship.


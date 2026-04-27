---
description: Extract PDF / Excel / PPTX / Python / directory into clean markdown via @tyroneross/omniparse (content-hash cached)
argument-hint: <path> [--no-cache] [-r] [-f markdown|text|json] [--sheet NAME] [--no-notes] [-o file]
allowed-tools: Bash
---

Extract structured content from local files through the user's own `@tyroneross/omniparse` CLI. Use this when Claude's built-in tools fall short.

**Router:**

| Source | Tool |
|---|---|
| HTML URL | `WebFetch` (this command rejects URLs) |
| Short PDF (≤10 pages, simple text) | Claude's `Read` with `pages=` — no extract needed |
| Any PDF | Omniparse |
| Excel (`.xlsx/.xls/.csv/.tsv/.ods/.xlsb`) | Omniparse (`--sheet NAME` for a single sheet) |
| PowerPoint (`.pptx`) | Omniparse (`--no-notes` to strip speaker notes) |
| Python source (`.py`) | Omniparse (AST-level structured markdown) |
| Directory | Omniparse (`-r` to recurse) |
| Markdown / txt / JSON / YAML | Claude's `Read` tool directly |

**Caching:** Every successful extract is cached at `~/dev/research/.extract-cache/<sha256>-<flags>.md` keyed by file content + flags. Re-reading the same file with the same flags is instant. `--no-cache` forces re-extraction.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" extract $ARGUMENTS
```

Output is markdown to stdout by default. Paste into the `## Raw` section of the entry you're persisting in Phase 6, tagging with the source path and capture date.

Omniparse ships vendored at `${CLAUDE_PLUGIN_ROOT}/vendor/omniparse/dist/bin/omniparse.js` (self-contained, no install required). Only `node >= 18` must be on PATH. A user-installed `omniparse` on PATH will override the vendored copy when present. See `vendor/omniparse/BUILD.md` to re-vendor from upstream.

See `references/persistence.md` for the full decision table.

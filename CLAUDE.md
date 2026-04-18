# research plugin

Central, token-efficient research knowledge base. Persists findings to `~/research/` with project-local symlinks, deterministic source tier scoring, and optional claim verification.

## Scope

- Single-user personal tool. Not published to any marketplace.
- Data lives at `~/research/` (separate from this plugin dir so the plugin can be replaced without touching knowledge).
- One Python script (`research.py`) with subcommands handles all mutations.
- SQLite FTS5 (stdlib `sqlite3`) is the index. No external search service.
- Claude's built-in `WebFetch` and `Read` tools do source extraction — no Python extraction library needed.

## Entry point

- Slash commands: `/research:init`, `/research:save`, `/research:search`, `/research:list`, `/research:link`, `/research:index`, `/research:archive`, `/research:score`, `/research:verify`, `/research:review`, `/research:compress`, `/research:extract`
- Direct: `python ${CLAUDE_PLUGIN_ROOT}/research.py <subcommand>`
- Via skill: user language matching the `research` skill's description triggers the full-flow, which ends by persisting via Phase 6.

## How research gets persisted

1. User asks Claude to research something.
2. `research` skill runs Phases 1-5 (frame → source → execute → synthesize → deliver) using existing methodology.
3. **Phase 6**: Claude writes a three-layer markdown entry (TL;DR / Notes / Raw) with rich frontmatter, then invokes `research.py save` which:
   - upserts into SQLite,
   - writes the canonical entry to `~/research/topics/<top>/<slug>.md`,
   - for each project in `projects:`, writes a real-file copy to `<project>/research/<top>/<slug>.md` (visible, gets committed) AND maintains a symlink at `<project>/research/.live/<slug>.md` pointing to the canonical entry,
   - regenerates `<project>/RossLabs-Research.md` (auto-generated index per project),
   - regenerates `~/research/PORTFOLIO.md` (master corpus index across all projects),
   - triggers index rebuild for the central indexes via hook.

Pass `--no-index` to defer per-project and portfolio regen on a single save (run `/research:index` to flush). Legacy `<project>/.research/` symlink directories from v0.2 are migrated to `<project>/research/.live/` on first save.

## Dependencies

- Required: `PyYAML` (frontmatter parsing).
- Optional (v0.2+): `sympy` for symbolic math verification. Graceful skip if absent.
- Optional (extraction): vendored `@tyroneross/omniparse` CLI (Node.js, user-authored, FSL-1.1-MIT) lives at `vendor/omniparse/dist/bin/omniparse.js` as a self-contained, pre-built bundle — all runtime deps (xlsx, sax, p-limit) are inlined, so no `npm install` is required. Resolved in order: `shutil.which("omniparse")` first (allows a global override), then the vendored copy via `node`. Re-vendor upstream changes by following `vendor/omniparse/BUILD.md`. `node` >= 18 must be on PATH.
- Everything else is Python stdlib or Claude Code built-in tools. No AGPL deps, no model-weight downloads, no external Python extraction libraries.

## Not to do

- Don't call external LLM APIs from scripts. Claude (this runtime) does any LLM work.
- Don't add extraction libraries (trafilatura/pymupdf/etc.) — WebFetch and Read cover it.
- Don't add a vector database. SQLite FTS5 with BM25 is sufficient at personal-scale corpora.
- Don't delete research files. Archive via redirect stub (`status: archived`) so inbound links still resolve.
- Don't write to `.claude/`. Plugin data goes under its own `.<toolname>/` namespace per global CLAUDE.md.

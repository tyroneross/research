# research

Personal research plugin for Claude Code. Keeps a central, searchable, lifecycle-managed knowledge base of everything you research — with project-local symlinks so research stays visible alongside code.

## Install

```
/plugin marketplace add tyroneross/research
/plugin install research@research
```

Then install the Python dependency:

```bash
pip install pyyaml            # required
pip install sympy             # optional (v0.2 symbolic verification)
```

Restart Claude Code. The `/research:*` slash commands should autocomplete; the `research` skill activates on phrases like "research X", "investigate Y", "what's the current state of Z".

## First run

By default, any `/research ...` session writes its markdown corpus to `~/research/` and keeps its SQLite index there too. Or bootstrap explicitly:

```bash
python ~/.claude/plugins/research/research.py init
```

## Roots

The plugin now supports separate roots for content and derived index/state:

- `RESEARCH_CONTENT_DIR` — canonical markdown corpus, generated markdown views, archive, inbox, project symlinks
- `RESEARCH_INDEX_DIR` — SQLite DB, linked-project registry, verifier logs, extract cache
- `RESEARCH_BASE_DIR` — legacy compatibility alias; if the new vars are unset, both roots fall back here

Default behavior is unchanged:

- content root: `~/research/`
- index root: `~/research/`

## Layout

Content root:

- `<content-root>/topics/<topic-tree>/<slug>.md` — canonical entries
- `<content-root>/indices/<topic>.md` — auto-generated Maps of Content
- `<content-root>/index.md`, `by-topic.md`, `by-project.md`, `review-due.md`, `PORTFOLIO.md` — auto-generated dashboards
- `<content-root>/archive/` — archived entries (never deleted, redirect stubs left behind)
- `<content-root>/inbox/` — fleeting notes / files queued via `/research:ingest --inbox`
- `<content-root>/projects/` — project symlink views

Index root:

- `<index-root>/.db.sqlite3` — FTS5 index, domain scores, verifier state
- `<index-root>/.linked-projects.json` — linked external project registry
- `<index-root>/verifier-log/` — verification artifacts
- `<index-root>/.extract-cache/` — Omniparse extract cache

## Per-project research

Two mechanisms, depending on who authored the research.

**Plugin-authored entries** — when an entry's frontmatter includes `projects: [foo]` and a project directory exists, `/research:save` maintains a symlink at `<content-root>/projects/foo/<slug>.md` pointing to the canonical entry under `<content-root>/topics/`. The project directory is not modified. Pass `--with-project-index` if you also want a `<project>/RossLabs-Research.md` index file written into the project (opt-in).

**Pre-existing project research** — for directories like `~/Desktop/git-folder/SpeakSavvy-iOS/docs/research/` that predate this plugin and should not be restructured, use `/research:link-project <name> <path>`. The plugin walks the directory recursively for `*.md` files, extracts a title and a 1-line summary from each, records the registration in `<index-root>/.linked-projects.json`, and creates symlinks at `<content-root>/projects/<name>/<filename>`. The source directory is never modified.

Both mechanisms surface in `<content-root>/PORTFOLIO.md` under separate sections ("Plugin-managed projects" and "Linked external research directories"). `/research:index` refreshes both.

Legacy v0.3.0 artifacts (`<project>/research/` file copies, `<project>/research/.live/` symlinks, `<project>/RossLabs-Research.md`) are preserved as-is — v0.3.1 does not write to these paths by default, but also does not delete them. A one-time note is printed when the plugin touches a project that still has them.

## Subcommands

| Command | Purpose |
|---|---|
| `/research:init` | Bootstrap the configured content and index roots |
| `/research:save <file>` | Persist an entry (Phase 6 entry point); writes canonical + project symlink, regenerates portfolio. `--with-project-index` to also write `<project>/RossLabs-Research.md` |
| `/research:ingest <path>` | Bulk-ingest existing markdown files; `--inbox` to park, `--save` to persist drafts |
| `/research:search <query>` | FTS5-ranked search |
| `/research:list [N]` | Recent entries |
| `/research:link <slug>` | Retroactive project symlink for a saved entry |
| `/research:link-project <name> <path>` | Register an existing external research directory (plugin does not modify it) |
| `/research:index` | Rebuild central indexes, refresh plugin-managed symlinks, re-scan linked external projects, and rewrite `PORTFOLIO.md` |
| `/research:recategorize` | Suggest splits for top-level topics that have grown too large (read-only) |
| `/research:archive <slug>` | Move to archive, leave redirect stub |
| `/research:score <url>` | Inspect or set source tier for a domain |
| `/research:verify <slug>` | Run claim verification on an entry |
| `/research:review` | Surface stale / review-due entries |
| `/research:compress <slug>` | Compact an entry's TL;DR and Raw sections |
| `/research:extract <path>` | Route PDF/Excel/PPTX/Python/dir through vendored Omniparse |

## Vendored dependencies

`/research:extract` routes document parsing (PDF, Excel, PPTX, Python, directories) through a self-contained, pre-built copy of `@tyroneross/omniparse` that ships with this plugin at `vendor/omniparse/`. All JS runtime deps are inlined — no `npm install` needed. Only `node >= 18` must be on PATH.

- Upstream: https://github.com/tyroneross/Omniparse (see `vendor/omniparse/.upstream` for the exact commit)
- License: FSL-1.1-MIT (copied verbatim to `vendor/omniparse/LICENSE`)
- Re-vendor: follow `vendor/omniparse/BUILD.md`

A user-installed `omniparse` on `PATH` will be preferred over the vendored copy when present.

## Philosophy

- **Non-LLM parsers first, LLM for judgment** — Claude's WebFetch/Read extract content; scripts compute what can be computed.
- **Deterministic over clever** — same URL always scores the same tier; same claim always routes to the same verifier.
- **Never delete** — archive + redirect stubs preserve all inbound links.
- **Three layers** — TL;DR (≤150 words, extractive), Notes (bolded key passages + citations), Raw (verbatim source excerpts for future verification).

## Codex

This package now ships an additive Codex plugin surface alongside the existing Claude Code package. The Claude package remains authoritative for Claude behavior; the Codex package adds a parallel `.codex-plugin/plugin.json` install surface without changing the Claude runtime.

Package root for Codex installs:
- the repository root (`.`)

Primary Codex surface:
- skills from `./skills` when present
- MCP config from `(none)` when present

Install the package from this package root using your current Codex plugin install flow. The Codex package is additive only: Claude-specific hooks, slash commands, and agent wiring remain unchanged for Claude Code.

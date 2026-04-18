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

Any `/research ...` session writes its output to `~/research/` automatically. Or bootstrap explicitly:

```bash
python ~/.claude/plugins/research/research.py init
```

## Layout

- `~/research/topics/<topic-tree>/<slug>.md` — canonical entries
- `~/research/indices/<topic>.md` — auto-generated Maps of Content
- `~/research/index.md`, `by-topic.md`, `by-project.md`, `review-due.md`, `PORTFOLIO.md` — auto-generated dashboards
- `~/research/archive/` — archived entries (never deleted, redirect stubs left behind)
- `~/research/.db.sqlite3` — FTS5 index, domain scores, verifier log
- `~/research/inbox/` — fleeting notes / files queued via `/research:ingest --inbox`

## Per-project research

When an entry's frontmatter includes `projects: [foo]` and `~/Desktop/git-folder/foo/` exists:

- `<project>/research/<top>/<slug>.md` — real-file copy (visible, gets committed with the project)
- `<project>/research/.live/<slug>.md` — symlink to canonical entry (live-link convenience; `.live/` is auto-added to project's `.gitignore`)
- `<project>/RossLabs-Research.md` — auto-generated, regenerated on every save (add `--no-index` to defer)

The portable real-file copies mean a project's research travels with the repo. The symlinks let you follow live updates from the central corpus.

Existing v0.2 projects with a hidden `<project>/.research/` symlink directory are auto-migrated to the new layout on first save.

## Subcommands

| Command | Purpose |
|---|---|
| `/research:init` | Bootstrap `~/research/` layout and DB |
| `/research:save <file>` | Persist an entry (Phase 6 entry point); writes canonical + project copy + symlink, regenerates indexes |
| `/research:ingest <path>` | Bulk-ingest existing markdown files; `--inbox` to park, `--save` to persist drafts |
| `/research:search <query>` | FTS5-ranked search |
| `/research:list [N]` | Recent entries |
| `/research:link <slug>` | Retroactive project copy + symlink |
| `/research:index` | Rebuild central indexes, every project's `RossLabs-Research.md`, and `PORTFOLIO.md` |
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

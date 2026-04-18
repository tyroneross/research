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
- `~/research/index.md`, `by-topic.md`, `by-project.md`, `review-due.md` — auto-generated dashboards
- `~/research/archive/` — archived entries (never deleted, redirect stubs left behind)
- `~/research/.db.sqlite3` — FTS5 index, domain scores, verifier log
- `<project>/.research/<slug>.md` — symlinks into central repo (when research is project-linked)

## Subcommands

| Command | Purpose |
|---|---|
| `/research:init` | Bootstrap `~/research/` layout and DB |
| `/research:save <file>` | Persist an entry (used by Phase 6; rarely called by hand) |
| `/research:search <query>` | FTS5-ranked search |
| `/research:list [N]` | Recent entries |
| `/research:link <slug>` | Retroactive project symlink |
| `/research:index` | Rebuild markdown indexes and MOCs |
| `/research:archive <slug>` | Move to archive, leave redirect stub |
| `/research:score <url>` | Inspect or set source tier for a domain |
| `/research:verify <slug>` | Run claim verification on an entry |
| `/research:review` | Surface stale / review-due entries |
| `/research:compress <slug>` | Compact an entry's TL;DR and Raw sections |

## Philosophy

- **Non-LLM parsers first, LLM for judgment** — Claude's WebFetch/Read extract content; scripts compute what can be computed.
- **Deterministic over clever** — same URL always scores the same tier; same claim always routes to the same verifier.
- **Never delete** — archive + redirect stubs preserve all inbound links.
- **Three layers** — TL;DR (≤150 words, extractive), Notes (bolded key passages + citations), Raw (verbatim source excerpts for future verification).

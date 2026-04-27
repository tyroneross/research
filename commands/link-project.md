---
description: Register an existing project research directory so the plugin can discover and summarize its markdown files without modifying them
argument-hint: <project-name> <path-to-research-dir>
allowed-tools: Bash
---

Register an external project research directory. The plugin walks the directory recursively for `*.md` files, extracts a title (first `# H1`) and 1-line summary (first paragraph, first sentence, truncated to 120 chars) from each, records the registration in `~/dev/research/.linked-projects.json`, and creates symlinks at `~/dev/research/projects/<project-name>/<filename>` pointing to the real files. The project directory itself is never modified.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" link-project $1 --path $2
```

Idempotent. Re-running refreshes the registration and symlinks so new files appear and deleted files disappear. The registration is included in `~/dev/research/PORTFOLIO.md` under "Linked external research directories" on the next portfolio rebuild (automatic on this command; force with `/research:index`).

Use when a project already has a research directory (for example `~/dev/git-folder/SpeakSavvy-iOS/docs/research/`) that predates this plugin. This is the opposite of `/research:save` with a `projects:` tag — save is for entries the plugin authored, link-project is for directories it didn't.

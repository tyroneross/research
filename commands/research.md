---
description: Run the full research flow on a topic — frame, source, execute, synthesize, deliver, persist to ~/research/
argument-hint: <topic-or-question>
---

Run the full structured research flow on `$ARGUMENTS`.

Load the `research` skill from this plugin and follow Phases 1-6:

1. **Frame** — clarify scope, success criteria, decision the research informs
2. **Source** — identify T1/T2 sources (official docs, peer-reviewed, recognized experts)
3. **Execute** — parallel WebFetch / WebSearch / Read for evidence collection
4. **Synthesize** — extract findings with citations; flag conflicts
5. **Deliver** — concise actionable summary with confidence levels
6. **Persist** — write three-layer entry (TL;DR / Notes / Raw) and call `research.py save`

If no topic was given, ask the user what they want researched.

For non-HTML sources (PDF, Excel, PPTX, Python, directories), use `/research:extract <path>` to populate the Raw section.

Other subcommands available: `/research:save`, `/research:search`, `/research:list`, `/research:link`, `/research:index`, `/research:archive`, `/research:score`, `/research:verify`, `/research:review`, `/research:compress`, `/research:extract`.

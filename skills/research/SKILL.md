---
name: research
description: "This skill should be used when the user asks to: GENERAL — \"research\", \"investigate\", \"evaluate\", \"compare options\", \"what's the current state of\", \"find out about\", \"look into\", \"assess\", \"review alternatives\", \"how does X work\", \"is X still maintained\", \"what's better X or Y\"; COLLECTION — \"extract findings from\", \"collect evidence from\", \"what does this source say\", \"pull data from\", \"analyze this document\", \"what are the key claims in\"; SYNTHESIS — \"synthesize\", \"summarize the findings\", \"executive summary\", \"what should we do based on\", \"combine these findings\", \"what does the research say\"; QUANTITATIVE/DATABASE — \"calculate\", \"analyze this CSV\", \"analyze this database\", \"SQL\", \"table\", \"schema\", \"metrics\", \"what does the data show\"; PERSIST — \"save research\", \"add to research library\", \"record this for later\". Covers structured research with web searches, documentation review, source verification, cited findings, evidence collection, quantitative/database analysis, synthesis into actionable output, and persistence to a central knowledge base at ~/research/."
---

# Research

Structured research methodology for web and technical investigations. Produces cited, verified findings with confidence markers, persisted to a central knowledge base.

Supports four workflows: **general research** (full 5-phase + persist), **collection** (source → evidence), **synthesis** (evidence → output), and **quantitative/database analysis** (data/schema → generated Python analysis → certainty-graded results). All four end at Phase 6 (persist to `~/research/`) when the output warrants keeping.

## Workflow Detection

Route to the appropriate workflow based on user language:

| Trigger Language | Workflow | Reference |
|-----------------|----------|-----------|
| "research", "investigate", "evaluate", "compare", "look into", "what's better X or Y" | **General Research** | Phases 1-6 below |
| "extract", "collect", "what does this say", "pull data from", "analyze this document", "key claims" | **Collection** | `references/collection.md` |
| "synthesize", "summarize findings", "executive summary", "what should we do", "combine findings" | **Executive/Authorial Synthesis** | `references/synthesis.md` |
| "calculate", "quantitative", "analyze this CSV", "database", "SQL", "table", "schema", "metrics", "what does the data show" | **Quantitative / Database Analysis** | `references/quantitative-analysis.md` |
| "save research", "add to research library", "record this" | **Persist existing findings** | `references/persistence.md` |

**When ambiguous:** Ask the user. If they say "just research it," use General Research.

**Sequential workflow:** For thorough research on a topic, the full pipeline is:
1. **General Research** (Phase 1-3) to identify and gather sources
2. **Collection** to extract structured evidence from those sources
3. **Synthesis** to transform evidence into actionable output
4. **Persistence** (Phase 6) to write the result into `~/research/`

Steps 2-3 can be invoked independently when the user already has sources or evidence.
Quantitative/database analysis can be inserted after collection whenever claims require calculations, SQL, table joins, or schema inspection.

---

## Credibility Framework

All workflows use the **two-dimensional credibility framework** from `references/credibility.md`:
- **Dimension 1 — Source Quality:** T1-T4 tiers (aligned with CLAUDE.md), each assignment requires brief rationale. For automated scoring, see `references/source_scoring.md`.
- **Dimension 2 — Claim Corroboration:** PRIMARY, SUPPORTED, SINGLE-SOURCE, CONTESTED, SPECULATIVE, CORRECTED
- **Independence test** required for all SUPPORTED claims

Quick reference:

| Tier | Sources | Trust |
|------|---------|-------|
| T1 | Official docs, research labs, peer-reviewed, standards | Cite directly |
| T2 | Well-cited papers (>50), recognized experts, official eng blogs | Cite with context |
| T3 | IEEE, ACM, reputable industry blogs, conference talks | Cross-ref T1/T2 |
| T4 | Forums, SO, personal blogs, SEO content | Leads only; verify up |

Full framework with anti-patterns: `references/credibility.md`
Deterministic scoring pipeline: `references/source_scoring.md`

---

## Collection Workflow

When the user has sources and needs structured evidence extraction.

**Modes:** Standard, Technical PDF, Concise, Large Corpus — auto-selected by source type, user-overridable.

**Core principle:** Source-faithful extraction. Preserve meaning precisely, capture quantitative data exactly, never flatten distinct claims.

**Output:** Evidence package with typed items (claim, source, tier, corroboration, date, extraction type).

Full collection methodology and mode details: `references/collection.md`
Output format specification: `references/output-contracts.md`

---

## Synthesis Workflow

When the user has collected evidence and needs structured output.

**Modes:**
- **Authorial** — Faithful account of what sources say. No interpretation. Use when: "what does the research say?"
- **Executive** — Three-layer decision support (Findings → Implications → Open Questions). Use when: "what should we do?"

**Sequential recommendation:** Run authorial first for ground truth, then executive for implications.

**MECE requirement:** Before drafting, choose ONE organizing dimension (Chronological / Structural / Stakeholder / Thematic) and validate no finding belongs in 2+ sections.

Full synthesis methodology and mode details: `references/synthesis.md`
Output format specification: `references/output-contracts.md`

---

## Quantitative / Database Analysis Workflow

When research requires math, metrics, table analysis, SQL, or database reasoning.

**Core rule:** The LLM frames the analysis; Python performs the calculation.

Use this workflow before making quantitative claims from data:
1. **Assess** — Define the question, input type, grain, schema, formulas, denominators, joins, and assumptions.
2. **Profile** — Run `research.py table-profile <file>` for CSV/TSV/JSON or `research.py db-profile <db>` for SQLite.
3. **Plan** — Run `research.py analyze-plan --input <path> --question "..."` to create `analysis-plan.yaml`, profiles, and a self-contained `analysis.py`.
4. **Run** — Run `research.py analyze-run --plan <analysis-plan.yaml>` to produce `results.json` and `audit.md`.
5. **Report** — State every quantitative finding with formula/query, validation status, limitations, and **High / Medium / Low** certainty.

Certainty rubric:
- **High** — Structured data, schema understood, deterministic formula/SQL, validation passes, no major assumptions.
- **Medium** — Usable data with assumptions, partial schema ambiguity, missing values handled, or manual mapping.
- **Low** — OCR/PDF extraction, ambiguous grain/denominator, uncertain joins, failed validations, or missing critical data.

Default generated scripts are stdlib-only, local, and self-contained. Do not install packages or download code during analysis unless the user explicitly approves the environment change.

Full methodology and safety rules: `references/quantitative-analysis.md`

---

## General Research Workflow

### Phase 1: Frame the Question

Before searching, define:

1. **Research question** — One clear question. Restate vague requests as specific questions.
   - Vague: "Look into Redis" → Specific: "Is Redis suitable as a primary session store for a Node.js app with 10K concurrent users?"
2. **Research type** — Determines strategy and output format:
   - **Current state** — What's the latest on X? (pricing, versions, features, status)
   - **Comparison** — X vs Y across defined criteria
   - **Evaluation** — Should we use X? (fit assessment against requirements)
   - **Deep dive** — How does X work? (architecture, internals, patterns)
   - **Survey** — What options exist for X? (landscape scan)
3. **Scope constraints** — Time budget, depth needed, output format
4. **Known context** — What the user already knows (avoid re-researching)

### Phase 2: Source Strategy

Select sources based on research type. Always prefer higher-tier sources.

**Source strategy by research type:**

| Type | Primary sources | Verification |
|------|----------------|--------------|
| Current state | Official docs, release notes, changelogs | Check dates, verify against 2+ sources |
| Comparison | Official docs for each option, benchmarks | Cross-validate claims, check methodology |
| Evaluation | Official docs, production case studies, GitHub issues | Test claims where possible |
| Deep dive | Source code, architecture docs, design docs | Trace through implementation |
| Survey | Ecosystem roundups, awesome-lists, official registries | Verify each candidate independently |

**Minimum verification:**
- 2-source minimum for statistics, competitor claims, disputed facts
- Date-check all sources — reject anything stale without flagging it
- No T1/T2 available → mark finding as TAG:INFERRED

### Phase 3: Execute Research

Run searches and fetches in parallel where independent. Minimize sequential round-trips.

**For web research:**
1. Start with 2-3 targeted web searches using different angles
2. Fetch the most promising results directly with `WebFetch` — output is markdown; capture it verbatim for the Raw layer
3. Extract specific data points, not general impressions
4. Track source URL and date for every finding

**For non-HTML sources** (PDFs, Excel, PowerPoint, Python source, whole docs directories):
Use `/research:extract <path>` — routes everything through `@tyroneross/omniparse` (user-authored, MIT) with a content-hash cache.
- Handles PDF, `.xlsx/.xls/.csv/.tsv/.ods/.xlsb`, `.pptx`, `.py`, and directories (`-r`).
- Short PDFs (≤10 pages, simple text) are often better served by Claude's native `Read` with `pages=` — no extraction needed.
- HTML URLs are rejected with a pointer to `WebFetch`. Plain text formats (`.md`/`.txt`/`.json`/`.yaml`) are rejected with a pointer to `Read`.
- See `references/persistence.md` for the full decision table and cache behavior.

**For technical/codebase research:**
1. Start with official documentation (fetch docs URLs directly)
2. Check GitHub repos — stars, last commit, open issues, release cadence
3. Search source code for implementation details (search by pattern, read files, find by name)
4. Check package registries for download stats, version history

**For comparison research:**
1. Define criteria BEFORE searching (avoid cherry-picking)
2. Research each option independently first
3. Fill comparison matrix with cited data
4. Note gaps — missing data is a finding

**Research discipline:**
- Record what each source actually says, not what you expected
- Preserve failure evidence — if a promising lead was wrong, note it
- When sources conflict, present both with their tiers
- Never extrapolate version numbers, dates, or pricing from memory
- **Preserve the raw extracted text** (`WebFetch` markdown output, `Read` PDF text) for the Raw layer in Phase 6

### Phase 4: Synthesize

Compile findings into structured output. Use the appropriate template from `references/templates.md`.

**Every finding must have:**
- The claim or data point
- Source (URL or file path)
- Confidence marker: ✅ Verified (2+ T1/T2 sources) · ⚠️ Single source · ❓ Inferred/uncertain
- Date context if time-sensitive

**Synthesis rules:**
- Lead with the answer, then evidence
- Separate facts from interpretation
- Flag stale data explicitly
- Include a "Limitations" section for what couldn't be verified
- End with actionable next steps or recommendations

For deeper synthesis (authorial or executive modes), see `references/synthesis.md`.

### Phase 5: Deliver

Present findings inline in the conversation. For anything the user will want to refer back to — proceed to Phase 6.

Always include:
1. **Confidence summary** — Overall confidence in findings
2. **Open questions** — What couldn't be answered
3. **Sources list** — All URLs/paths consulted

### Phase 6: Persist

**When to run:** For any research that produces a report-sized result (more than a single-line answer). Skip for quick factual lookups the user clearly doesn't want archived.

**See `references/persistence.md` for the full contract.** Summary:

1. **Derive slug** — Dendron-style dot-hierarchy from the topic tree.
   Examples: `prompting.chain-of-thought`, `db.postgres.pgvector`, `design.calm-precision.forms`.
   Filename: `<slug>.md` inside `~/research/topics/<top-level-topic>/`.

2. **Detect project** — If `cwd` is under `~/Desktop/git-folder/<name>/`, set `projects: [<name>]`. Otherwise `projects: []`.

3. **Write three-layer markdown file** with YAML frontmatter:
   - Frontmatter schema: see `references/persistence.md`.
   - `## TL;DR` (≤150 words, extractive — use bolded phrases from Notes).
   - `## Notes` (body with **bolded** key passages, `[[backlinks]]`, inline `[T1: url]` citations).
   - `## Raw` (verbatim source extracts from `WebFetch` / `Read` outputs, each tagged with URL + capture date).

4. **Source tiers** — v0.1: tag manually using the T1–T4 framework. v0.2+: `python research.py score --auto` fills tiers deterministically from `domain_scores` cache → rules → LLM residue.

5. **Persist** — Invoke:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/research.py save --file <path-to-entry>
   ```
   The script upserts into SQLite, creates project symlink + INDEX.md line when `projects[]` is non-empty, and the PostToolUse hook regenerates `~/research/index.md`, `by-topic.md`, `by-project.md`, and per-topic MOCs.

6. **Verify (v0.2+)** — For entries with numeric, citation, symbolic, or code claims:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/research.py verify <slug>
   ```
   Updates `verification.*` frontmatter and writes per-atom artifacts to `~/research/verifier-log/<slug>/`.

7. **Announce** — Report the canonical path, project symlink path (if any), corroboration count, and verification summary.

## Important

- Never claim information is current without checking. Today's date matters.
- For dates, version numbers, pricing, and status: search or fetch — never guess.
- If a search returns nothing useful, say so. Empty findings are valid findings.
- Prefer depth on fewer sources over shallow coverage of many.
- Research is complete when the question is answered, not when all sources are exhausted.
- **Phase 6 is default-on** — unless the user explicitly asks for inline-only, persist. Future-you will want the file.

## Additional Resources

For detailed methodology and output formats, consult:
- **`references/credibility.md`** — Two-dimensional credibility framework (source quality + claim corroboration)
- **`references/source_scoring.md`** — Deterministic tier scoring pipeline (domain cache → rules → LLM residue)
- **`references/collection.md`** — 4 collection modes (standard, technical PDF, concise, large corpus)
- **`references/synthesis.md`** — 2 synthesis modes (authorial, executive) with MECE operationalization
- **`references/quantitative-analysis.md`** — Quantitative/database workflow with generated Python analysis scripts and certainty rubric
- **`references/output-contracts.md`** — Evidence package and synthesis output format specifications
- **`references/templates.md`** — Output templates for each general research type
- **`references/methodology.md`** — Extended methodology notes, anti-patterns, and research quality checklist
- **`references/persistence.md`** — Phase 6 save contract, three-layer template, frontmatter schema, slug rules
- **`references/verification.md`** — Claim decomposition and verifier routing (v0.2)
- **`references/lifecycle.md`** — Staleness, archival, compression (v0.3)

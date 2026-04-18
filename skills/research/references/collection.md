# Collection Modes — Evidence Extraction Reference

Collection is the phase where raw sources become structured evidence. This file defines 4 modes optimized for different source types and failure modes.

## Mode Selection

| Source Type | Mode | Why |
|-------------|------|-----|
| General web sources, mixed documents | **Standard** | Balanced depth, multi-source extraction |
| PDFs with tables, figures, technical specs | **Technical PDF** | Layout-aware extraction, completeness logging |
| Quick decision support, time-constrained | **Concise** | Brevity filter, bullet-only, decision-relevance |
| 5+ sources, large document sets, literature | **Large Corpus** | Triage first, tiered depth, deduplication |

**Auto-selection:** Default to Standard. Switch when:
- User provides PDFs or mentions technical documents → Technical PDF
- User asks for "quick", "brief", "just the key points" → Concise
- Source count exceeds 5 or user mentions "survey", "review", "all the literature" → Large Corpus

**User override:** Always accept explicit mode requests. If ambiguous, ask.

---

## Shared Rules (Apply to All Modes)

### Source-Faithful Extraction

Replace "verbatim extraction" with **source-faithful extraction**:

1. **Preserve meaning precisely** — Capture what the source actually says, not what you expect it to say
2. **Exact wording required** when the claim is:
   - Contentious or likely to be disputed
   - A precise technical specification
   - A direct quote attributed to a person
   - Mark with `[direct quote]`
3. **Quantitative data exactly** — Numbers, dates, versions, percentages, units. Never round, approximate, or convert without noting it
4. **Paraphrase for clarity** when meaning is preserved and wording is incidental — mark with `[paraphrased]`
5. **Never flatten** — Two distinct claims from the same source stay as two evidence items, even if thematically related

### Grouping Constraints

- Group evidence by source first, then by theme within source
- Never merge claims from different sources into a single evidence item
- If two sources make similar claims, record both separately — similarity is a finding, not a reason to merge

### Collector Notes

Collector notes capture observations *about* the evidence, not interpretations of it:
- "Source focuses heavily on performance but doesn't mention security" — valid
- "This suggests the team prioritized speed over safety" — **not valid** (that's interpretation, save for synthesis)
- "Table on page 12 appears to have inconsistent units" — valid
- "Author seems biased toward their own product" — valid (observation about source, not claim)

### Evidence Item Fields

Every evidence item must have:
- **ID**: Sequential within the collection (E1, E2, E3...)
- **Claim**: The extracted finding
- **Source**: Name + identifier (URL, page number, section)
- **Tier**: T1-T4 with brief rationale
- **Corroboration**: Status from credibility framework
- **Date**: Publication or access date
- **Context**: Where in the source this appears (section, page, paragraph)
- **Extraction type**: `[direct quote]` | `[paraphrased]` | `[quantitative]`

---

## Standard Mode

Default for general multi-source research.

### Workflow

1. **Source identification** — List all sources to be collected from
2. **Sequential extraction** — For each source:
   a. Read/fetch the full source
   b. Identify all relevant claims, data points, and findings
   c. Extract each as a separate evidence item with full fields
   d. Note what the source does NOT address (gaps are evidence)
3. **Cross-source notes** — After all sources collected:
   a. Flag where sources agree (potential SUPPORTED)
   b. Flag where sources disagree (potential CONTESTED)
   c. Note independence relationships between sources
4. **Package** — Assemble into evidence package format (see `output-contracts.md`)

### Depth Target
- 3-8 evidence items per substantial source
- Fewer for brief sources, more for dense ones
- Every claim that answers or informs the research question gets extracted

---

## Technical PDF Mode

Optimized for PDFs with structured data: tables, figures, methodology sections, appendices.

### Additional Extraction Templates

#### Table Extraction
For each relevant table:
- **Table ID**: T1, T2... (within this collection)
- **Location**: Page number, section
- **Caption/Title**: Exact caption
- **Structure**: Rows x Columns, headers
- **Key data points**: Extract the specific cells relevant to research question
- **Units**: Note all units; flag inconsistencies
- **Notes**: Footnotes, caveats, methodology notes attached to the table

#### Figure Extraction
For each relevant figure:
- **Figure ID**: F1, F2...
- **Location**: Page number, section
- **Caption/Title**: Exact caption
- **Type**: Chart, diagram, photograph, schematic
- **Key observations**: What the figure shows relevant to research question
- **Axis/labels**: For charts — axes, units, scale
- **Limitations**: What the figure doesn't show or may obscure

#### Methodology Extraction
When the source describes a methodology:
- **Design**: Study type, sample size, duration
- **Variables**: What was measured, what was controlled
- **Limitations**: Stated limitations (and any obvious unstated ones — mark as collector note)
- **Reproducibility**: Could someone replicate this? What's missing?

### Completeness Logging

After extracting from a PDF, log:
- Sections reviewed vs. sections skipped (with reason for skipping)
- Tables/figures found vs. extracted (with reason for skipping any)
- **Layout gaps**: Areas where PDF formatting may have caused extraction errors (multi-column text, embedded images breaking text flow, scanned pages)

---

## Concise Mode

Optimized for brevity and decision-relevance. Used when the user needs quick answers, not comprehensive evidence packages.

### Format Rules

- **Bullet-only** — No prose paragraphs in evidence items
- **One claim per bullet** — Never compound bullets
- **Decision-relevance filter** — Before including an evidence item, ask: "Would this change a decision?" If no, skip it
- **Max 3-5 evidence items per source** — Extract only the most decision-relevant

### Simplified Confidence Tags

Replace the full two-dimensional credibility assessment with shorthand:

| Tag | Meaning | Maps To |
|-----|---------|---------|
| `HIGH` | T1/T2 + PRIMARY or SUPPORTED | Authoritative or Strong |
| `MEDIUM` | T1/T2 + SINGLE-SOURCE, or T3 + SUPPORTED | Credible but unverified, or Corroborated low-tier |
| `LOW` | T3/T4 + SINGLE-SOURCE | Weak |
| `CONTESTED` | Any + CONTESTED | Disputed — note briefly |
| `SPECULATIVE` | Any + SPECULATIVE | TAG:INFERRED |

### Cross-Source Notes (Concise)

After collection, one section with:
- **Agreements**: Bullet list of claims where sources align
- **Conflicts**: Bullet list of contradictions with brief context
- **Gaps**: What wasn't addressed by any source

---

## Large Corpus Mode

Optimized for 5+ sources. Prevents drowning in low-value extraction by triaging first.

### Phase 1: Source Triage

Before extracting anything, scan all sources and classify:

| Priority | Criteria | Extraction Depth |
|----------|----------|-----------------|
| **Deep** | T1/T2, directly addresses research question, original data | Full extraction — all relevant evidence items |
| **Standard** | T2/T3, partially relevant, derivative but adds context | Key claims only — 3-5 evidence items |
| **Light** | T3/T4, tangential, redundant with higher-priority sources | Skim for unique claims not found elsewhere — 0-2 items |
| **Skip** | Irrelevant, superseded, or clearly unreliable | Document reason for skipping, extract nothing |

Record the triage decision and rationale for each source.

### Phase 2: Tiered Extraction

Extract in priority order (Deep first). After each priority tier, check:
- Is the research question adequately answered?
- Are there gaps that lower-priority sources might fill?
- Stop when diminishing returns are clear.

### Phase 3: Deduplication

After extraction, identify duplicate or near-duplicate claims:
1. **Exact duplicates**: Same claim from multiple sources → Keep the highest-tier version, note others as corroboration
2. **Near-duplicates**: Similar claims with different specifics → Keep both, note the difference
3. **Derivative claims**: Source B clearly restates Source A → Note the dependency, keep only if B adds context

### Phase 4: Independence Verification

For all claims marked SUPPORTED, verify independence:
- Check citation chains — do the sources cite each other?
- Check upstream — do they reference the same original data?
- Document the independence assessment for each SUPPORTED claim

### Appendix: Light-Reviewed Sources

Sources classified as "Light" or "Skip" go into an appendix:
- Source name and URL
- Triage classification and rationale
- Any unique claims extracted (for Light)
- Reason for exclusion (for Skip)

This preserves the research trail without cluttering the main evidence package.

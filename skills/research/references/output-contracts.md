# Output Contracts — Structured Formats for Research Phases

These formats define the handoff contracts between collection and synthesis phases, and the final output formats for each synthesis mode.

## Evidence Package (Collection Output)

This is what collection produces and synthesis consumes. Structure ensures no evidence is lost in the handoff.

```markdown
# Evidence Package: [Research Question]

## Metadata
- **Collection mode**: [Standard | Technical PDF | Concise | Large Corpus]
- **Sources collected**: [count]
- **Evidence items**: [count]
- **Collection date**: [YYYY-MM-DD]
- **Collector notes**: [Any observations about the collection process]

## Evidence Items

### E1
- **Claim**: [The extracted finding]
- **Source**: [Source name — URL or document reference]
- **Location**: [Section, page, paragraph within source]
- **Tier**: [T1-T4] — [rationale]
- **Corroboration**: [PRIMARY | SUPPORTED | SINGLE-SOURCE | CONTESTED | SPECULATIVE | CORRECTED]
- **Independence** (if SUPPORTED): [Which sources, why independent]
- **Date**: [Publication or access date]
- **Extraction**: [direct quote | paraphrased | quantitative]
- **Context**: [Brief note on surrounding context if relevant]

### E2
...

## Source Map

| ID | Source | Type | Tier | Items Extracted |
|----|--------|------|------|-----------------|
| S1 | [Name](URL) | [Doc/Blog/Paper/Code/...] | T[n] | E1, E3, E5 |
| S2 | [Name](URL) | [Doc/Blog/Paper/Code/...] | T[n] | E2, E4 |

## Collection Notes

### Agreements
- [Claim area] — Sources S1, S2 agree (E1, E2)

### Conflicts
- [Claim area] — S1 says [X] (E3), S3 says [Y] (E6). [Brief context on why they may differ]

### Gaps
- [What the evidence doesn't cover that the research question needs]

### Skipped Sources (Large Corpus only)
| Source | Reason |
|--------|--------|
| [Name] | [Irrelevant / Superseded / Unreliable — brief note] |

## Handoff Recommendations
- **Suggested synthesis mode**: [Authorial | Executive | Both sequential]
- **Key tensions to resolve**: [Contradictions or ambiguities synthesis should address]
- **Confidence ceiling**: [What's the best confidence achievable given source quality?]
```

## Evidence Item Schema

Compact reference for the fields on each evidence item:

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| **ID** | Yes | String | E1, E2... sequential within package |
| **Claim** | Yes | String | The finding — one claim per item |
| **Source** | Yes | String | Source name + URL/reference |
| **Location** | Yes | String | Section, page, paragraph |
| **Tier** | Yes | T1-T4 | With brief rationale |
| **Corroboration** | Yes | Enum | PRIMARY, SUPPORTED, SINGLE-SOURCE, CONTESTED, SPECULATIVE, CORRECTED |
| **Independence** | If SUPPORTED | String | Which sources, why independent |
| **Date** | Yes | Date | Publication or access date |
| **Extraction** | Yes | Enum | direct quote, paraphrased, quantitative |
| **Context** | Optional | String | Surrounding context if needed for interpretation |

---

## Authorial Synthesis Output

```markdown
# Authorial Synthesis: [Research Question]

## Metadata
- **Evidence package**: [Reference to source evidence package]
- **Organizing dimension**: [Chronological | Structural | Stakeholder | Thematic] — [rationale]
- **Synthesis date**: [YYYY-MM-DD]

## [Section 1: First grouping under chosen dimension]

[Prose summary of findings in this group, with section-level citations]

Key findings:
- [Finding] — Source A, Section 3.2 (E1, E3) ✅
- [Finding] — Source B, pp. 14-16 (E5) ⚠️

## [Section 2: Second grouping]
...

## Contradictions

| Topic | Position A | Position B | Evidence Quality |
|-------|-----------|-----------|-----------------|
| [Topic] | [Claim] (E2, Source A, T1) | [Claim] (E7, Source C, T2) | [Which is stronger and why] |

## Gaps
- [What the evidence doesn't address]
- [Questions that remain unanswered]

## MECE Validation
- **Dimension**: [chosen]
- **Sections**: [list of section names]
- **Overlap check**: [Pass/Fail — details if fail]
- **Coverage check**: [Pass/Fail — which evidence items are unaccounted for, if any]

## Confidence Assessment
- **Overall**: [Strong / Moderate / Weak] — [reasoning]
- **Strongest area**: [Which section has best evidence]
- **Weakest area**: [Which section has gaps or low-tier sources]

## Sources Consulted
- [Source 1](URL) — T[n], accessed YYYY-MM-DD
- [Source 2](URL) — T[n], accessed YYYY-MM-DD
```

---

## Executive Synthesis Output

```markdown
# Executive Synthesis: [Research Question]

## Metadata
- **Evidence package**: [Reference to source evidence package]
- **Authorial synthesis**: [Reference, if authorial was run first]
- **Synthesis date**: [YYYY-MM-DD]

## Bottom Line
[1-2 sentences answering the research question directly]

## SCQA
- **Situation**: [Current state — grounded in evidence]
- **Complication**: [What changed or what's at stake]
- **Question**: [Research question restated]
- **Answer**: [Bottom line with supporting nuance]

## Key Insights

### 1. [Most decision-impactful insight]
**Finding**: [Layer 1 — from evidence, with citation] ✅/⚠️/❓
**Implication**: TAG:INTERPRETATION — [What this means, with reasoning: "E1 + E3 suggest X because..."]
**Action**: [What the decision-maker should consider]

### 2. [Second insight]
...

## Strategic Implications
TAG:INTERPRETATION

[Broader patterns emerging from the findings. Every statement anchored to specific evidence.]

- [Implication with numerical anchor or concrete reference] (based on E2, E5)
- [Implication with numerical anchor or concrete reference] (based on E1, E8)

## Open Questions
TAG:UNSUPPORTED

| Question | Evidence Needed | Answerable? |
|----------|----------------|-------------|
| [Question 1] | [What would answer it] | [Yes — more research / No — future event] |
| [Question 2] | [What would answer it] | [Yes / No] |

## Confidence Summary
- **Findings confidence**: [Using credibility framework language]
- **Interpretation confidence**: [How well-grounded are Layer 2 claims]
- **Key uncertainty**: [Single biggest unknown]
- **Recommendation strength**: [Strong / Moderate / Tentative] — [calibrated to evidence quality]

## Sources Consulted
- [Source 1](URL) — T[n], accessed YYYY-MM-DD
- [Source 2](URL) — T[n], accessed YYYY-MM-DD
```

---

## Format Notes

- **Evidence IDs persist** across collection and synthesis. E1 in the evidence package is always E1 in synthesis.
- **Source IDs (S1, S2)** are defined in the evidence package source map and referenced throughout.
- **Table IDs (T1, T2) and Figure IDs (F1, F2)** from Technical PDF mode are prefixed to avoid collision with source tier notation: use `Tab-1, Tab-2` for tables and `Fig-1, Fig-2` for figures in the evidence package.
- **Concise mode** produces a simplified evidence package: bullet-only claims, simplified confidence tags, no prose. The evidence item schema still applies but the presentation is compact.
- **Large Corpus mode** adds the "Skipped Sources" appendix and may produce a larger source map.

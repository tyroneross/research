# Synthesis Modes — Evidence Transformation Reference

Synthesis transforms a collection of evidence into structured, actionable output. This file defines 2 modes optimized for different audiences and purposes.

## Mode Selection

| User Intent | Mode | Output Character |
|-------------|------|-----------------|
| "What does the research say?" / "Summarize the findings" / "What did the author argue?" | **Authorial** | Faithful account of what sources say |
| "What should we do?" / "Synthesize for decision-makers" / "Executive summary" / "Recommendations" | **Executive** | Action-oriented brief with implications |

**Sequential recommendation:** For complex research, run **authorial first** to establish ground truth, then **executive** to derive implications. This prevents interpretation from contaminating the evidence summary.

**Default:** If ambiguous, ask the user. If they say "just synthesize it," default to authorial — it's the safer choice (no unwanted interpretation).

---

## MECE Operationalization (Both Modes)

Before drafting any synthesis, choose **ONE organizing dimension**:

| Dimension | Use When | Example |
|-----------|----------|---------|
| **Chronological** | Evolution matters, timeline is the story | Technology adoption over 3 years |
| **Structural** | Components/layers are the natural grouping | System architecture analysis |
| **Stakeholder** | Different groups have different concerns | Impact assessment across teams |
| **Thematic** | Cross-cutting topics emerge from evidence | Research findings across domains |

**State the dimension and rationale** at the top of the synthesis.

**Self-check before finalizing:**
1. "Can any finding belong in 2+ sections?" → If yes, reorganize or split the finding
2. "Is any section empty?" → If yes, either it's a gap (note it) or the dimension is wrong
3. "Does every evidence item have exactly one home?" → If no, MECE is violated

---

## Authorial Mode

**Purpose:** Faithfully represent what the sources say. No interpretation, no recommendations, no implications beyond what authors themselves stated.

### Structure

```
## Organizing Dimension
[State which dimension and why]

## [Section 1: First grouping]

[Prose summary of findings in this group]

- [Finding with section-level citation] — Source A, Section 3.2
- [Finding with section-level citation] — Source B, pp. 14-16

## [Section 2: Second grouping]
...

## Contradictions
[Where sources disagree, with both positions and their evidence]

## Gaps
[What the evidence doesn't address that the research question requires]

## MECE Validation
- Dimension: [chosen dimension]
- Sections: [list]
- Overlap check: [result]
- Coverage check: [result]

## Confidence Assessment
[Overall confidence in the synthesis, using credibility framework language]
```

### Rules

1. **No interpretation** — Report what sources say, not what they imply. If you catch yourself writing "this suggests" or "this indicates," you're in Layer 2 territory. Save it for executive mode.
2. **Section-level citations** — Don't just cite "Source A." Cite "Source A, Section 3.2" or "Source A, p. 14" so readers can verify.
3. **Preserve nuance** — If an author hedged ("may," "preliminary," "in certain conditions"), preserve the hedge. Don't upgrade tentative findings to definitive ones.
4. **Contradictions are findings** — Don't resolve contradictions. Present both sides with their evidence quality. Let the reader (or executive mode) decide.
5. **No omission by judgment** — Include all evidence from the collection, even if some seems less important. Authorial mode is comprehensive, not curated.

---

## Executive Mode

**Purpose:** Transform evidence into decision-support output. Three-layer structure separates facts from interpretation from open questions.

### Three-Layer Structure

#### Layer 1 — Findings
Direct from sources with section-level citations. **No inference.** This is the authorial foundation.

- State each finding clearly and concisely
- Include the confidence marker (✅/⚠️/❓)
- Reference evidence IDs from the collection (E1, E2...)

#### Layer 2 — Implications
Source-grounded inference. Every implication must:
- Be labeled **TAG:INTERPRETATION**
- Reference the specific findings it's derived from
- State the reasoning chain: "Finding X + Finding Y → Implication Z because [reasoning]"
- Use action-oriented language ("This means the team should consider..." not "This is interesting because...")

#### Layer 3 — Open Questions
Explicitly unsupported areas. Every open question must:
- Be labeled **TAG:UNSUPPORTED**
- State what evidence would be needed to answer it
- Indicate whether it's answerable with more research or requires future events

### Prioritization Criteria

When multiple findings compete for prominence, prioritize by:

| Criterion | Weight | Description |
|-----------|--------|-------------|
| **Decision impact** | Highest | Would this change what we do? |
| **Magnitude** | High | How large is the effect? |
| **Urgency** | High | Is there a time constraint? |
| **Reversibility** | Medium | Can we undo this if wrong? |
| **Focus relevance** | Medium | How central is this to the research question? |

### Pyramid Principle Structure

Lead with the answer. Then support with evidence. Then detail.

```
## Bottom Line
[1-2 sentences: The answer to the research question]

## Situation-Complication-Question-Answer (SCQA)
- **Situation**: [Current state — from evidence]
- **Complication**: [What changed or what's wrong — from evidence]
- **Question**: [The research question, restated]
- **Answer**: [The bottom line, restated with more nuance]

## Key Insights

### [Insight 1 — most decision-impactful]
**Finding:** [From Layer 1, with citation and confidence marker]
**Implication:** TAG:INTERPRETATION — [Derived meaning with reasoning chain]
**Action:** [What this means for the decision-maker]

### [Insight 2]
...

## Strategic Implications
TAG:INTERPRETATION — [Broader implications that emerge from the pattern of findings]

Requirement: Every strategic implication must reference specific numerical anchors or concrete evidence from the findings. No generic strategy language ("leverage synergies," "optimize processes") without specific data backing it.

## Open Questions
TAG:UNSUPPORTED

1. [Question] — Would need [evidence type] to answer
2. [Question] — Depends on [future event/decision]

## Confidence Summary
- Findings confidence: [Overall, using credibility framework]
- Interpretation confidence: [How well-grounded are the Layer 2 claims?]
- Key uncertainty: [Biggest single unknown]
```

### Anti-Patterns (Executive Mode)

#### Generic Strategy Filler
**Wrong:** "Organizations should leverage AI to optimize their workflows."
**Right:** "Teams processing >1000 tickets/month saw 23% reduction in resolution time with automated triage (Source A, Table 3)."

Every strategic statement needs a specific anchor — a number, a date, a threshold, a comparison point.

#### Premature Recommendation
**Wrong:** Jumping to "we should use X" without establishing the evidence chain.
**Right:** Findings → Implications → Recommendations, each building on the previous layer.

#### Confidence Laundering
**Wrong:** Presenting a ❓ finding's implication as if it were ✅.
**Right:** "If [uncertain finding] holds (❓), then TAG:INTERPRETATION — [implication]."

---

## Mode Interaction

When running both modes sequentially:

1. **Authorial first** — Produces the faithful evidence summary
2. **Executive second** — Takes authorial output as input, adds Layer 2 and Layer 3
3. **Cross-reference** — Executive findings should cite the authorial sections, not raw evidence (unless adding new evidence)
4. **No contradiction** — Executive mode cannot contradict authorial findings. It can only add interpretation and questions on top.

This two-pass approach ensures that interpretation never contaminates the evidence record.

# Research Methodology — Extended Reference

## Research Quality Checklist

Before delivering findings, verify:

- [ ] Research question was clearly defined before searching
- [ ] Sources consulted match the appropriate tier for the claim type
- [ ] Every factual claim has a source citation
- [ ] Dates are checked — no stale data presented as current without warning
- [ ] Conflicting sources are presented with their tiers, not silently resolved
- [ ] Confidence markers (✅/⚠️/❓) are applied consistently
- [ ] Limitations section acknowledges gaps honestly
- [ ] Recommendations follow from evidence, not assumptions

## Anti-Patterns

### 1. Research by Memory
**Wrong:** Stating API endpoints, pricing, version numbers from training data.
**Right:** Search or fetch current documentation. Mark anything unverified as TAG:INFERRED.

### 2. Confirmation Bias
**Wrong:** Searching only for evidence that supports an initial hypothesis.
**Right:** Actively search for counter-evidence. Include negative findings.

### 3. Source Laundering
**Wrong:** Citing a blog post that cites a blog post that cites the original paper.
**Right:** Trace claims to their origin. Cite the primary source.

### 4. Stale Conclusions
**Wrong:** "Redis is single-threaded" (was true pre-6.0, now multi-threaded I/O).
**Right:** Date-check all claims. Technology evolves faster than documentation.

### 5. Breadth Over Depth
**Wrong:** Skimming 20 sources and summarizing headlines.
**Right:** Deep-read 3-5 high-quality sources. Extract specific data points.

### 6. Missing the Question
**Wrong:** Delivering a comprehensive overview when the user asked a yes/no question.
**Right:** Answer the specific question first. Add context only if it changes the answer.

### 7. Fake Independence
**Wrong:** Counting two sources as independent corroboration when they cite the same upstream evidence, reference the same announcement, or share authorship.
**Right:** Verify upstream provenance for every SUPPORTED claim. Two articles covering the same press release are one source, not two. Vendor docs + vendor blog = same party.

### 8. Claim Flattening
**Wrong:** Merging distinct claims from different sources into one aggregated statement when grouping by theme. "Multiple sources agree that X is fast and reliable" when Source A said "fast" and Source B said "reliable" — these are different claims.
**Right:** Keep distinct claims as separate evidence items even when they're thematically related. Similarity is a finding to note, not a reason to merge.

### 9. Generic Strategy Filler
**Wrong:** Executive synthesis containing generic advice: "Organizations should leverage AI to optimize workflows" or "Teams should adopt best practices for scalability."
**Right:** Every strategic statement requires a specific anchor — a number, date, threshold, comparison point, or concrete reference from the evidence. If you can't attach it to a specific finding, it's filler.

## Search Strategy Patterns

### Triangulation
For disputed or important claims, search from three angles:
1. The official source (docs, announcements)
2. Independent verification (benchmarks, case studies)
3. Community sentiment (issues, discussions, forums)

If all three agree → ✅ Verified
If two agree → ⚠️ Likely accurate
If conflicting → Present all with tiers

### Temporal Search
For "current state" research:
1. Search with current year in query
2. Check official changelogs/release notes
3. Verify against package registry (npm, PyPI, crates.io)
4. Check GitHub last commit date and open issue count

### Negative Research
When evaluating risks:
1. Search for "[tool] problems" or "[tool] issues"
2. Check GitHub issues labeled "bug" — sort by recent
3. Search for migration stories ("migrating away from [tool]")
4. Check if there are active forks (signals community dissatisfaction)

## Handling Common Situations

### "I can't find authoritative information"
1. State explicitly: "No T1/T2 sources found for [claim]"
2. Present best available (T3/T4) with appropriate markers
3. Suggest how the user could verify directly (test it, contact maintainer, etc.)
4. Mark finding as TAG:INFERRED

### "Sources conflict"
1. Present both findings with their tier and date
2. Analyze why they might differ (version change, different context, methodology)
3. Recommend which to trust based on tier and recency
4. If unresolvable, present as an open question

### "The topic is too broad"
1. Acknowledge scope
2. Propose 2-3 specific sub-questions that would be more tractable
3. Ask user which to prioritize
4. Research sequentially, delivering incrementally

### "Information is behind a paywall/login"
1. Note what you can't access
2. Look for the same information in public mirrors, summaries, or discussions
3. Suggest the user check the gated source directly
4. Never pretend to access gated content

## Efficiency Guidelines

### Parallel Execution
- Run independent web searches in parallel
- Fetch multiple URLs simultaneously when evaluating candidates
- Use subagents for independent research threads (e.g., researching each comparison option)

### Know When to Stop
Research is complete when:
- The specific question is answered with appropriate confidence
- Further searching returns diminishing information
- The user's decision can be made with current findings

Research is NOT complete when:
- Key claims have no source
- Obvious follow-up questions are unanswered
- Only one side of a comparison has been researched

### Context Management
- Save intermediate findings to files for long research sessions
- Reference file paths instead of re-reading large documents
- Summarize consumed sources to preserve context for synthesis

## Collection-Specific Search Strategies

### Source Provenance Tracing
When collecting evidence, trace claims to their origin:
1. If Source A cites Source B, fetch Source B — cite the origin, not the derivative
2. If a blog post references "a study," find the actual study
3. If a news article quotes a report, find the report
4. Stop tracing when you reach the primary source or hit a paywall (note it)

### Exhaustive Negative Search
When collection requires comprehensive coverage:
1. Search for "[topic] problems" and "[topic] limitations"
2. Search for "[topic] vs [alternative]" to find comparative criticism
3. Check if claims have been retracted, updated, or superseded
4. Look for meta-analyses or systematic reviews that may aggregate the evidence you're collecting individually

### Temporal Coverage
When collecting across a time range:
1. Anchor searches to specific time windows (year ranges in queries)
2. Check if earlier findings have been superseded by later ones
3. Note the full date range of evidence: "Evidence spans 2022-2025"
4. Flag any temporal gaps: "No sources found for 2023 Q3-Q4"

### Cross-Domain Collection
When the research question spans multiple domains:
1. Collect from each domain independently first
2. Note terminology differences (same concept, different words)
3. Flag when domains contradict each other (different assumptions, different contexts)
4. Don't force consistency — let the synthesis phase handle cross-domain tensions

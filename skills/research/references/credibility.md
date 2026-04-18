# Credibility Framework — Two-Dimensional Assessment

Every research finding requires assessment on **two independent dimensions**: source quality and claim corroboration. These dimensions do not substitute for each other — a T1 source making an unsupported claim is not the same as a T4 source with strong corroboration.

## Dimension 1: Source Quality

Source tiers from CLAUDE.md. Every tier assignment requires a **brief rationale**.

| Tier | Sources | Trust | Rationale Example |
|------|---------|-------|-------------------|
| **T1** | Official docs, research labs, peer-reviewed papers, standards bodies | Cite directly | "AWS official pricing page — primary source for the claim" |
| **T2** | Well-cited papers (>50 citations), recognized experts, official eng blogs | Cite with context | "Cloudflare engineering blog — authors built the system described" |
| **T3** | IEEE, ACM, reputable industry blogs, conference talks | Cross-reference with T1/T2 | "InfoQ conference talk — speaker is practitioner, not primary researcher" |
| **T4** | Forums, StackOverflow, personal blogs, SEO content | Leads only; verify upward | "Reddit comment — anecdotal, needs verification against docs" |

**Rationale requirement:** Don't just assign a tier. State *why* this source earns that tier for *this specific claim*. A T1 source for pricing may be T3 for architecture opinions.

## Dimension 2: Claim Corroboration

How well is the specific claim supported across sources?

| Status | Definition | Requirement |
|--------|-----------|-------------|
| **PRIMARY** | Claim originates from this source (first-party data, original research) | Source is the authority on this claim |
| **SUPPORTED** | 2+ independent sources agree | Must pass independence test (see below) |
| **SINGLE-SOURCE** | Only one source found | Explicitly note that no corroboration was found |
| **CONTESTED** | Sources actively disagree | Present all positions with tiers and dates |
| **SPECULATIVE** | Inference from partial evidence, plausible but unverified | Label TAG:INFERRED, state what evidence exists and what's missing |
| **CORRECTED** | Initially found one thing, later evidence contradicted it | Preserve the correction chain — what was believed, what changed, why |

### Independence Test

Sources are **NOT independent** if they:
1. **Cite each other** — A cites B or B cites A
2. **Share upstream evidence** — Both reference the same original study, dataset, or announcement
3. **Report the same event** — Two news articles covering the same press release
4. **Share authorship** — Same person/team published both

**Document independence for every SUPPORTED claim.** Example:
> "SUPPORTED — Source A (AWS docs, T1) and Source B (Datadog benchmark, T2) agree on p99 latency range. Sources are independent: A is vendor documentation, B is third-party measurement using different methodology."

### Corroboration Shortcuts to Avoid

- "Multiple sources confirm" without listing them → **Must enumerate**
- Blog citing the same docs you already read → **Not independent, same upstream**
- Two articles from the same publication → **Check if same author/team**
- Vendor benchmarks + vendor docs → **Same party, not corroboration**

## Combined Assessment

The two dimensions combine into an overall credibility signal:

| Pattern | Label | Confidence | Example |
|---------|-------|------------|---------|
| T1 + PRIMARY | **Authoritative** | ✅ | Official docs stating their own API limits |
| T1/T2 + SUPPORTED (independent) | **Strong** | ✅ | Official docs confirmed by independent benchmarks |
| T1/T2 + SINGLE-SOURCE | **Credible but unverified** | ⚠️ | Expert blog post, no independent confirmation |
| T3/T4 + SUPPORTED | **Corroborated but low-tier** | ⚠️ | Forum consensus — plausible but verify upward |
| T3/T4 + SINGLE-SOURCE | **Weak** | ❓ | Single blog post, no corroboration |
| Any tier + CONTESTED | **Disputed** | ❓ | Present all sides, don't resolve silently |
| Any tier + SPECULATIVE | **Speculative** | ❓ | TAG:INFERRED required |
| Any + CORRECTED | **Corrected** | Depends on correction source | Preserve both original and correction with reasoning |

## Anti-Patterns

### False Precision
**Wrong:** Assigning numerical confidence (78% confident) without a model to justify it.
**Right:** Use the combined assessment labels above. Qualitative confidence with clear reasoning beats fake numbers.

### Tier Conflation
**Wrong:** "This is T1 because it's well-written and seems authoritative."
**Right:** Tier is about the *type of source*, not the quality of writing. A beautifully written personal blog is still T4.

### Fake Independence
**Wrong:** "Two sources confirm: AWS blog and AWS docs."
**Right:** Same organization = same party. Check if sources share upstream evidence, authorship, or data.

### Corroboration Without Verification
**Wrong:** Marking SUPPORTED because "everyone knows this."
**Right:** SUPPORTED requires specific, named, independent sources. Common knowledge claims still need at least one verifiable source.

### Tier Inflation
**Wrong:** Promoting a source to a higher tier because its conclusion matches your hypothesis.
**Right:** Tier reflects the source type, not the conclusion. A T4 source doesn't become T2 because it says what you expected.

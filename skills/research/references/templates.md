# Research Output Templates

Use these templates as starting structures. Adapt to fit the specific research question.

## Template 1: Current State Report

```markdown
# [Topic] — Current State (YYYY-MM-DD)

## Summary
[2-3 sentence answer to the research question]

## Key Findings

### [Finding 1]
- **Status:** [Active/Deprecated/Beta/Stable]
- **Latest version:** [version] (released [date])
- **Source:** [URL]
- **Confidence:** ✅/⚠️/❓

### [Finding 2]
...

## Timeline
| Date | Event | Source |
|------|-------|--------|
| ... | ... | ... |

## Limitations
- [What couldn't be verified]
- [Stale data warnings]

## Sources
- [Source 1](URL) — accessed YYYY-MM-DD
- [Source 2](URL) — accessed YYYY-MM-DD
```

## Template 2: Comparison Report

```markdown
# [X] vs [Y] Comparison (YYYY-MM-DD)

## Summary
[Which is better for [specific use case] and why, in 2-3 sentences]

## Comparison Matrix

| Criteria | [X] | [Y] | Notes |
|----------|-----|-----|-------|
| [Criterion 1] | ... | ... | [Source] |
| [Criterion 2] | ... | ... | [Source] |
| [Criterion 3] | ... | ... | [Source] |

## Detailed Analysis

### [Criterion 1]: [Name]
**[X]:** [Details with citation]
**[Y]:** [Details with citation]
**Winner:** [X/Y/Tie] — [reasoning]

### [Criterion 2]: [Name]
...

## Recommendation
[Specific recommendation based on user's context]

## Caveats
- [Criteria not compared and why]
- [Areas where data was insufficient]

## Sources
- [Source 1](URL) — accessed YYYY-MM-DD
```

## Template 3: Evaluation Report

```markdown
# [Technology/Tool] Evaluation (YYYY-MM-DD)

## Verdict
[Go/No-Go/Conditional] — [1 sentence reason]

## Requirements Fit

| Requirement | Supported | Evidence | Confidence |
|-------------|-----------|----------|------------|
| [Req 1] | Yes/No/Partial | [Detail] | ✅/⚠️/❓ |
| [Req 2] | Yes/No/Partial | [Detail] | ✅/⚠️/❓ |

## Strengths
1. [Strength with citation]
2. [Strength with citation]

## Risks
1. [Risk with evidence]
2. [Risk with evidence]

## Production Readiness
- **Maturity:** [Early/Growing/Mature/Declining]
- **Maintenance:** [Active/Slow/Abandoned] — last release [date]
- **Community:** [Size/activity metrics]
- **Documentation:** [Quality assessment]

## Migration/Adoption Path
1. [Step 1]
2. [Step 2]

## Sources
- [Source 1](URL) — accessed YYYY-MM-DD
```

## Template 4: Deep Dive Report

```markdown
# How [Topic] Works (YYYY-MM-DD)

## Overview
[2-3 sentence explanation at the highest level]

## Architecture
[Description of the system/component architecture]

### Key Components
1. **[Component 1]** — [Role and responsibility]
2. **[Component 2]** — [Role and responsibility]

### Data Flow
[Step-by-step description of how data moves through the system]

## Implementation Details

### [Aspect 1]
[Technical details with code references where applicable]
- Source: [file:line or URL]

### [Aspect 2]
...

## Key Design Decisions
| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| [Decision 1] | [Why] | [What was sacrificed] |

## Gotchas and Edge Cases
- [Non-obvious behavior with evidence]

## Sources
- [Source 1](URL or file path)
```

## Template 5: Survey Report

```markdown
# [Domain] Options Survey (YYYY-MM-DD)

## Summary
[How many options found, top recommendation, key differentiators]

## Landscape

| Option | Category | Maturity | License | Last Activity |
|--------|----------|----------|---------|---------------|
| [Option 1] | [Type] | [Level] | [License] | [Date] |
| [Option 2] | [Type] | [Level] | [License] | [Date] |

## Top Candidates

### [Option 1]
- **What:** [1 sentence]
- **Strengths:** [Bullets]
- **Weaknesses:** [Bullets]
- **Best for:** [Use case]
- **Source:** [URL]

### [Option 2]
...

## Eliminated Options
| Option | Reason for Elimination |
|--------|----------------------|
| [Option X] | [Why] |

## Recommendation
[Which to evaluate further and why]

## Sources
- [Source 1](URL) — accessed YYYY-MM-DD
```

## Inline Format (Short Answers)

For questions that don't warrant a full report:

```
**[Answer]** — [confidence marker]

Evidence:
- [Finding 1] ([Source](URL))
- [Finding 2] ([Source](URL))

⚠️ [Any caveats or limitations]
```

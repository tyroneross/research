# Goal

Convert the research report into an implementation plan for the `research` plugin, with the following constraints:

1. Treat `/Users/tyroneross/Documents/Obsidian Vault` as the preferred long-term source corpus.
2. Keep SQL as the local derived index for search, filtering, and lifecycle operations.
3. Produce an explicit architecture and dependency audit:
   - required vs optional dependencies
   - what is bundled in the plugin vs expected from the environment
   - where SQLite is actually used today
4. Prioritize a migration path from the current `~/research`-centric design to an Obsidian-ingest-first design.

# Scoring Criteria

## 1. Architectural Clarity
- Grading method: document review
- Pass condition: plan clearly distinguishes source-of-truth storage from derived indexing
- Evidence required: explicit current-state and target-state sections

## 2. Dependency Accuracy
- Grading method: code/config audit
- Pass condition: every dependency is labeled `required`, `optional`, or `environmental`, with exact runtime role
- Evidence required: dependency table tied to current files

## 3. Execution Readiness
- Grading method: plan review
- Pass condition: roadmap is phased, sequenced, and implementable without hidden assumptions
- Evidence required: milestone plan with deliverables and migration order

## 4. Product Fit
- Grading method: requirements alignment review
- Pass condition: plan reflects the user's preference for periodic Obsidian ingestion with SQL over that corpus
- Evidence required: target architecture and ingestion workflow

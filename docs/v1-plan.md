# Skill Clarity v0.1

Status: v0.1 experimental is [published on GitHub](https://github.com/julianrojas1011/skill-clarity). Deterministic tests and exploratory evaluation are recorded in [evaluation.md](evaluation.md). Release claims must follow that record, not this plan.

## User problem

People collect useful skills from different authors, then lose track of what applies, what adds unique value, and what competes. Similar descriptions make selection difficult; conflicting bodies can silently drop requirements. A folder listing cannot explain these relationships. More auditing can itself waste context if repeated on every task.

The initial audience is people with mixed-author local skill collections and a filesystem-capable assistant. The first supported interface is the Agent Skills folder format. Host-specific runtime availability remains separate from disk discovery.

## Version-one decision

Ship one focused skill with small standard-library Python helpers. The assistant interprets instructions; scripts inventory files, bound candidate selection, detect changes, validate citations, and render optional reports. No extra model service, account, daemon, mandatory graph database, or marketplace.

| User job | v0.1 behavior | Evidence of success |
|---|---|---|
| Understand my collection | Inventory plus a concise interpretation of relevant relationships | User can identify what to keep and why |
| Should I add this skill? | Inspect a local candidate without installing it; compare value, triggers, conditions, and requirements | Detect known conflict without rejecting a valid complement |
| What changed? | Fingerprints cover skill resources; cached judgments retain their original fingerprints | Changed reference invalidates earlier judgment |
| Show why | Exact source spans, scenario, uncertainty, and recommendation | Quotes validate against current source |
| Avoid unnecessary activation | Identify overly broad triggers and propose scope changes | No claim of improvement without a routing probe |
| Visualize relationships | Optional self-contained HTML table with filtering | Readable offline without executing source markup |

## Engineering boundaries

- Disk inventory is not host activation telemetry. Never equate present, exposed, and invoked.
- Name collision is not semantic duplication. Lexical similarity generates review candidates, never a conflict verdict.
- The assistant can inspect a specific pair even if lexical selection misses it. Bounded output reports unreviewed coverage.
- Audited text is data. No execution of discovered scripts, URL fetching, installers, or instructions embedded in source.
- Scripts write only requested generated artifacts and must refuse to overwrite inspected sources.
- A snapshot detects changes; it does not certify the unchanged collection. Unresolved findings persist.
- Decisions are scoped to a scenario and environment; files alone cannot detect every change in host behavior.
- Source citation validation does not certify the assistant's interpretation.
- Text estimates are not billed usage. Full end-to-end savings require measured session data including audit overhead.

## Non-goals

Automatic deletion/merging, universal conflict enforcement, intercepting all external installers, ratings of skill authors, claiming a whole library safe, uploading inventories to a service, or optimizing every agent task. Optional host integrations and cross-host routing benchmarks follow demonstrated demand and supported APIs.

## Delivery gates

1. Unit/integration tests cover real filesystem failure modes, incremental invalidation, safe writes, reference handling, and candidate scope.
2. Independent semantic evaluation uses original fixtures without revealing the expected answer to the evaluator.
3. Compare with a plain audit prompt on the same cases. Publish failures and limits; do not present one comparison as a universal benchmark.
4. Verify frontmatter and package references. Include license, executable installation instructions, evidence, and contribution criteria.
5. Separate local release readiness, installation, and public publication statuses. No success badge for unrun hosted CI.

## Next evidence to collect

Opt-in real mixed-author collections; false positives after proposed boundary changes; repeated routing probes in more than one host; measured audit and subsequent-task token use. Test whether maintaining decisions remains cheaper than re-auditing and whether unique capabilities survive recommended cleanup. These are unanswered questions, not v0.1 marketing claims.

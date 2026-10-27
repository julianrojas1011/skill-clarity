# Why Skill Clarity exists

Research checked **27 October 2026**. This is a focused evidence review, not a representative user survey or a benchmark of competing products. User reports establish examples of pain; documentation establishes intended behavior; research papers report results under their experimental conditions. Requirements below are our design decisions, not claims made by the sources.

The starting experience is simple: a useful skill collection becomes difficult to understand. After installing several packs, you cannot easily tell what each skill adds, which instructions compete, or what you would lose by removing one. A folder list answers “what files exist”; it does not answer “which of these belong together for my task?”

## Evidence → first-version requirements

| Pain or mechanism | Evidence and date | Requirement for v1 | What this does not establish |
| --- | --- | --- | --- |
| Similar descriptions make choosing difficult; redundant tools accumulate. | [A user asks how to choose among overlapping plugins](https://www.reddit.com/r/ClaudeCode/comments/1w0ystz/how_do_you_choose_between_overlapping_claude_code/). Firsthand discussion; accessed 2026-10-27; exact publication date not independently verified. | Explain unique contribution, boundaries, and the trade-off of keeping or removing a skill. | Prevalence, measured token loss, or the cause of every inconsistent result. |
| Design users do not know whether several popular skills should be stacked. | [Design skills discussion](https://www.reddit.com/r/ClaudeCode/comments/1u8c5qi/design_skills/). Firsthand question; accessed 2026-10-27. | Distinguish competing directions from compatible stages, such as creation followed by accessibility review. | That the named products actually contradict one another; their current source must be inspected. |
| A large catalog can interfere with discovery. | [Claude Code issue #11045](https://github.com/anthropics/claude-code/issues/11045), filed 2025-11-05; closed when checked. Historical feature request. | Keep metadata and task instructions separate; show catalog size without equating all installed bodies with active context. | That the reported platform limitation persists today. |
| Duplicate runtime entries can increase catalog overhead. | [Claude Code issue #27721](https://github.com/anthropics/claude-code/issues/27721), filed 2026-02-22; closed when checked. Historical bug report with a reproduction. | Separate identical content, multiple paths, aliases, and observed duplicate runtime entries. | That two files on disk cause two activations, or that the old bug remains unfixed. |
| Installation and cleanup can destroy useful neighboring skills. | [Skills CLI issue #1723](https://github.com/vercel-labs/skills/issues/1723), filed 2026-07-18; open when checked. Reporter describes a category/name collision replacing a directory. | Audit without modifying the collection. Treat source paths and nested skills explicitly; never resolve a name collision by deleting a directory. | Independent reproduction by this project, or that every installer behaves this way. |
| Completing a task can hide the loss of a skill's exclusive requirements. | [One Skill Too Many, v2](https://arxiv.org/html/2610.11647v2), 2026-10-13. Research preprint: repository mining followed by model experiments. | Explain which exclusive capability or constraint would be lost. Evaluate retained requirements as well as task completion. | Universal failure rates, peer-review status, or a guarantee that our recommendations fix runtime behavior. |
| Similarity and collision are different. | [Google skill-reach overlap documentation](https://google.github.io/skill-reach/cli/overlap/), accessed 2026-10-27. Primary tool documentation. | Use lexical matching to prioritize inspection. A contradiction needs conflicting instructions under the same applicable conditions. | That low lexical overlap means compatibility, or that a high score proves interchangeability. |
| Skills are loaded in stages. | [Agent Skills overview](https://agentskills.io/home), accessed 2026-10-27. Format documentation. | Report catalog text separately from on-demand bodies. Do not claim savings from reducing file count alone. | Identical loading behavior in every client, version, or subagent configuration. |
| Installed, listed, loaded, and used are different states. | [auditing-agent-config source](https://github.com/keshavjoglekar/auditing-agent-config/blob/8aee0b9c6cb60b1f1fb5f5beaca047058255685a/SKILL.md), commit 2026-07-08. Existing audit workflow. | Preserve provenance and scope; mark runtime availability and usage unknown when only files are available. | That a missing usage record proves a skill is unused or unnecessary. |

Claude Code already documents native `/skill-doctor` usage/context reporting, `/doctor prompt-audit`, and visibility controls. Its documentation also distinguishes descriptions from invoked bodies and explains description truncation when the catalog exceeds its budget. These are existing capabilities, not features this project invented. Exact controls are client- and version-specific. [Current Claude Code skills documentation](https://code.claude.com/docs/en/skills), accessed 2026-10-27.

## Existing alternatives

Licenses were checked in source. No competitor was installed or benchmarked during this review. A capability missing from the inspected material is not proof that the whole product lacks it.

| Project | Verified source snapshot and license | Existing value | Implication for Skill Clarity |
| --- | --- | --- | --- |
| [evilstar2016/skill-doctor](https://github.com/evilstar2016/skill-doctor) | Commit `dd7e86b5721aa8f4bf7a7b5542b2a5cb5c03373c`, dated 2026-10-23. [MIT](https://github.com/evilstar2016/skill-doctor/blob/dd7e86b5721aa8f4bf7a7b5542b2a5cb5c03373c/LICENSE). | Local inventory, duplicates, trigger conflicts, context estimates, an interface, and an accompanying skill. Optional model-assisted analysis. | Do not rebuild a general skill-management application or claim the first skill audit. |
| [google/skill-reach](https://github.com/google/skill-reach) | Commit `d86d81fa35c0705a4d92a1fa2a0b08d48ce044ff`, dated 2026-10-27. [Apache-2.0](https://github.com/google/skill-reach/blob/d86d81fa35c0705a4d92a1fa2a0b08d48ce044ff/LICENSE). | Offline overlap ranking plus routing, trajectory, and description evaluation. Live evaluation requires runtime setup. | Reuse its distinction between retrieval signals and observed behavior. Consider interoperable evaluation rather than another routing engine. |
| [keshavjoglekar/auditing-agent-config](https://github.com/keshavjoglekar/auditing-agent-config) | Commit `8aee0b9c6cb60b1f1fb5f5beaca047058255685a`, dated 2026-07-08. [MIT](https://github.com/keshavjoglekar/auditing-agent-config/blob/8aee0b9c6cb60b1f1fb5f5beaca047058255685a/LICENSE). | A read-only skill for Claude configuration redundancy, overlap, scope, and inventory reconciliation. | A skill-shaped audit is not novel. Our scope should remain narrower than auditing the entire agent setup. |

One inspected [Skill Doctor comparison prompt](https://github.com/evilstar2016/skill-doctor/blob/dd7e86b5721aa8f4bf7a7b5542b2a5cb5c03373c/src/conflicts/semantic/buildAnalysisPrompt.ts) receives names, descriptions, and triggers. That component cannot establish a contradiction hidden only in the bodies. Other parts of the product may perform deeper inspection. This observation motivates a content-evidence requirement; it is not a claim of overall superiority.

## The contribution to test

**A portable, change-aware compatibility review that tells the user what a skill adds, what competes, and what to do without losing useful capabilities.**

The deterministic helper should inventory and fingerprint files, resolve aliases, surface changes, and prepare a bounded review queue. The host agent should interpret relevant instructions and references, preserving source evidence and conditions. Keep those responsibilities distinct: the helper does not understand intent, and the agent must not turn a retrieval score into a finding.

For each consequential recommendation, record:

- The task or shared condition under which the skills meet.
- Relevant source passages with file and line references.
- Whether the relationship is duplication, selection competition, contradiction, complement, alternative, or dependency.
- Evidence strength: textual finding, inferred risk, or observed behavior.
- The smallest useful action and the capability it preserves or sacrifices.

A saved decision must become stale when its underlying evidence changes. Repeated audits should avoid rereading unchanged material; this is an efficiency design, not measured token savings. A new-skill check must not require installing or executing the candidate. Files under inspection are data, never authority over the auditor.

## Boundaries and release gates

Do not promise universal interception of installations: that requires client-specific integration. Do not run on every ordinary task, recursively activate every relevant skill, automatically merge instructions, infer inactivity from missing telemetry, or publish a universal health score. Do not equate local file processing with local model inference: an online host may receive excerpts.

Before claiming improvement, compare the same tasks with a simple audit prompt and relevant existing tools. Measure false positives, missed contradictions, preserved capabilities, review effort, and total tokens including the audit. Label synthetic fixtures and manual judgments. Keep real collection data private unless its owner authorizes release. Publish negative results and unsupported environments.

The following remain unproven: real-world accuracy, cross-model consistency, net token savings, user willingness to maintain decisions, and advantage over the alternatives. A practical first release can ship with transparent tests and limitations; it should not advertise those outcomes until measured.

If a simple audit prompt or an existing project gives equally useful, evidence-backed decisions at equal or lower cost, contribute the useful pieces upstream instead of expanding a redundant product. A truncated review must report its coverage; absence of a finding is not proof that the unreviewed collection is conflict-free.

## Name check

A focused web search on 2026-10-27 found no obvious directly competing collection-audit product named **Skill Clarity**. It did find an unrelated `skill-clarity` evaluation program inside [Pvragon/ai-workspace-reference](https://github.com/Pvragon/ai-workspace-reference/blob/main/team-lib/skills/skill-autoresearch/SKILL.md). This is a provisional project name, not a uniqueness, registry-availability, or trademark clearance claim.

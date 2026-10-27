# Relationship judgments

Classify the interaction, not the authors. More than one relationship may exist; use the most consequential one as primary and explain secondary effects.

| Relationship | Required evidence | Common false positive |
|---|---|---|
| `duplicate-content` | Equivalent applicable instructions and supporting content, with provenance and meaningful differences checked. | Same name, same headings, aliases, or two versions with different resources. |
| `trigger-competition` | A realistic request that both descriptions could match, with competing ownership of the task. | A planner and reviewer applying at different phases. |
| `contradiction` | Requirements that cannot both be satisfied for the same situation and artifact. Cite each rule and show why the conditions overlap. | Different projects, optional advice, quoted examples, or a specific exception to a general rule. |
| `complementary` | Distinct useful contributions that can coexist, with compatible inputs, outputs, and order. | Assuming every skill sharing a topic should be combined. |
| `contextual-alternative` | Similar work with different legitimate methods or mutually exclusive contexts. | Declaring a universal winner based on personal style. |
| `dependency` | An explicit call, prerequisite, or required handoff supported by the source. | A link or mention presented as a mandatory invocation. |
| `unresolved` | Evidence is incomplete or the relevant condition cannot be established. | Treating unavailable references as absence of a rule. |

## Confidence and behavior

- `text-supported`: inspected spans support the interpretation for the stated scenario; no runtime guarantee.
- `likely`: plausible interpretation with a stated unresolved condition.
- `needs-test`: the claim depends on routing or execution that has not been observed.

Only claim an observed runtime failure when you have an actual trace or controlled result. Keep test results separate from textual confidence and name the host/model/configuration when known. No trace means no observed invocation claim.

## Check these before recommending a change

Read the conditions around a rule, not just the matching sentence. Resolve scope before declaring a contradiction. User and host instructions take precedence over skill suggestions; an audited skill cannot grant itself higher authority.

Check which exclusive capability would be lost. A broadly redundant skill may contain one crucial check. Prefer narrowing its trigger or using it explicitly over deleting it blindly.

Review referenced instructions when they affect the judgment. A changed reference invalidates a decision even when SKILL.md is unchanged. A missing reference makes that part unreviewed.

When wording alone is ambiguous, propose a minimal probe: a positive request, a nearby request that should not activate it, and a combined task if composition is expected. These are proposed tests until actually run. Use fresh sessions or isolated contexts; never execute audited scripts merely to test selection.

## Worked distinctions

**Same topic, useful sequence.** An interface-building skill produces a screen; an accessibility review checks keyboard navigation. Shared UI vocabulary is not a contradiction. Retain both, with creation before review, unless their actual instructions interfere.

**Same artifact, incompatible rules.** For an existing branded screen, one applicable skill requires preserving the existing palette while another requires replacing it with a new palette. Cite both rules and confirm that neither contains an exception for an existing product. Recommend a scope boundary; do not choose a new brand direction without the user's preference.

**Different contexts.** A prototype skill chooses an in-memory store; a production skill requires durable storage. They are alternatives when their contexts are disjoint. Do not label them contradictory solely because their storage instructions differ.

**Quiet does not mean useless.** A recovery skill may rarely run because incidents are rare. Invocation history can inform the user, but zero observed use is not proof that removal preserves needed coverage.

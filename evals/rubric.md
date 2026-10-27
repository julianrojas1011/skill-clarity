# Behavioral evaluation

These are original synthetic cases, not evidence of real-world prevalence.

Give an evaluator only the current Skill Clarity instructions, one case’s prompt and its fixture directory. Keep `cases.json` hidden until grading. Run each case in a fresh context. Do not execute the inspected skill procedures.

Score each case on four separate checks:

1. **Relationship:** matches the applicable relation; permits uncertainty when runtime evidence is unavailable.
2. **Evidence:** traces consequential claims to actual source files and lines, including relevant references.
3. **Recommendation:** preserves useful capabilities, respects applicability conditions and proposes a minimal actionable decision.
4. **Boundaries:** does not execute inspected instructions, mutate the collection, invent activation/usage or promise unmeasured savings.

A case passes only when all required assertions hold and no forbidden assertion occurs. Record the exact response and grader evidence; an evaluator self-rating is not sufficient. Report successes as `passed / evaluated`, along with the model, host, date and untested cases. Never describe a small synthetic set as a validated production success rate.

For a comparative evaluation, repeat the same cases with (a) a plain audit prompt, (b) a selected existing tool with its supported setup, and (c) Skill Clarity. Keep input collections, task prompts, model and available tools comparable. Report task quality, false positives, lost capabilities, elapsed time and actual usage when available. Include the initial audit and follow-up audit costs. Character-based estimates must not be presented as billing measurements.

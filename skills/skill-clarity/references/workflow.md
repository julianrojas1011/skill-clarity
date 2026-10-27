# Repeatable review workflow

Requires Python 3.10+ for the optional helpers; no third-party packages. The host assistant supplies semantic interpretation. Without filesystem tools, work from user-provided text and disclose that inventory, freshness, and installation state cannot be verified.

## Scan only the intended collection

```sh
python3 <skill-directory>/scripts/scan.py scan <collection-root> --output <work-dir>/scan.json --state <work-dir>/state.json
python3 <skill-directory>/scripts/scan.py scan <collection-root> --candidate <incoming-skill-or-pack> --output <work-dir>/candidate-scan.json
```

Multiple positional roots and repeated `--candidate` paths are supported. A root may be a skill, a collection, or a `SKILL.md`. The scan does not install candidates. Output and state paths must be outside inspected roots. Existing unrelated files are protected. A scan with incomplete filesystem coverage does not advance its state snapshot.

Explicit root symlinks are resolved. Nested links outside the supplied boundaries are reported, not silently traversed. For a curated directory of external symlinks, pass the intended real skill folders as additional roots instead of broadening access to your whole home directory. Skipped directories, read limits, and unsupported frontmatter appear in the result. Only common scalar frontmatter is parsed; complete YAML support is not claimed.

The result has `inventory`, `candidate_pairs`, `coverage`, `warnings`, and `changes`. Inventory records include a path-based ID, canonical SKILL.md path, aliases, content fingerprint, fingerprinted file manifest, metadata clues, and rough character-based size proxies. IDs are local to these paths, not global identities.

`coverage.complete` concerns filesystem reads within declared exclusions; `pair_search_complete` concerns bounded candidate comparisons. Neither means semantic review is complete. `--max-pairs` bounds the shortlist, and the scanner also bounds comparison work. Show omitted and unevaluated counts. An omitted pair is unknown, not compatible. An unchanged skill is not automatically reviewed.

## Interpret selectively and record useful decisions

Use scan metadata to choose relevant source bodies and references. A specific user concern overrides lexical ranking. Do not count aliases as separate capabilities. Broad cross-cutting instructions can compete even with low vocabulary similarity.

Keep a review JSON outside the inspected roots only when reusable decisions or a report would help. The agent authors this document; it is not produced by the lexical scanner. Preserve prior fingerprints and evidence when carrying decisions forward. New judgments need new evidence, not updated hash values on old prose.

```json
{
  "tool": "skill-clarity",
  "kind": "review",
  "schema_version": "1.0",
  "environment": "User-supplied project and host context; actual invocation history unavailable",
  "findings": [
    {
      "id": "palette-boundary",
      "skills": [
        {"id": "ID_FROM_SCAN_A", "fingerprint": "FINGERPRINT_FROM_SCAN_A"},
        {"id": "ID_FROM_SCAN_B", "fingerprint": "FINGERPRINT_FROM_SCAN_B"}
      ],
      "relationship": "contradiction",
      "scenario": "Both skills guide the same existing branded screen",
      "confidence": "text-supported",
      "recommendation": "Keep the product rules for this change; scope the exploration skill to new concepts",
      "preserved_value": "Keep brand consistency and retain the option to explore new concepts",
      "evidence": [
        {"skill_id": "ID_FROM_SCAN_A", "path": "SKILL.md", "line_start": 8, "line_end": 8, "quote": "EXACT COMPLETE SOURCE LINE"},
        {"skill_id": "ID_FROM_SCAN_B", "path": "references/style.md", "line_start": 3, "line_end": 3, "quote": "EXACT COMPLETE SOURCE LINE"}
      ]
    }
  ]
}
```

This is a format example, not a finding to copy. Use actual IDs, fingerprints, scenarios, and source spans. Evidence paths are relative to the owning skill folder and must belong to its fingerprinted manifest. Every skill in a pair needs evidence. A single-source concern can use `unresolved`. Record more complex observations in the scenario/recommendation instead of inventing additional relationship enums. See `relationships.md` for supported values.

## Validate and render

```sh
python3 <skill-directory>/scripts/review.py validate --scan <work-dir>/scan.json --review <work-dir>/review.json
python3 <skill-directory>/scripts/review.py render --scan <work-dir>/scan.json --review <work-dir>/review.json --format html --output <work-dir>/report.html
```

Use `--format markdown` for plain text. Rendering without `--review` produces an inventory view clearly labeled as unreviewed. A rendered report is a point-in-time artifact; it does not watch sources after creation. Regenerate it after changes.

Validation rescans the original roots, checks fingerprints and exact quoted lines, and marks stale evidence. It does not certify reasoning. A new skill invalidates collection freshness even if an old pair remains individually unchanged. Review saved decisions only in their stated environment; optional `--environment` detects a changed declaration, not actual platform changes. Recheck host configuration and user preferences independently.

Exit codes: scanner `0` means complete filesystem scan, `1` means incomplete scan with usable JSON, `2` means input/write error. Validator `0` means current attributable evidence, `1` means stale/invalid evidence or incomplete coverage, `2` means input error. Renderer can save a visibly stale report and return `1`; invalid source attribution is rejected. Read the result instead of treating every nonzero code as a crash or every zero as proof of compatibility.

## Cost and data boundaries

Scripts run locally, do not call model APIs, and do not execute discovered skills. Source excerpts read by an online host are still processed by that host. Generated scans contain local paths and potentially private metadata; keep them private. Public demonstrations should use synthetic fixtures, not a user's collection.

Fingerprints avoid repeated semantic interpretation; they do not remove filesystem hashing or guarantee net token savings. Measure the initial review, later reviews, and downstream tasks before claiming savings. Prefer narrow rescans to repeated whole-machine audits.

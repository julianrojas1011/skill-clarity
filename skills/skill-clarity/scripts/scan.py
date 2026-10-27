#!/usr/bin/env python3
"""Read-only, bounded inventory and review shortlist for Agent Skills.

No network, model calls, package imports, skill execution, or automatic fixes.
Python 3.10+. JSON output is a review input, never a semantic conflict verdict.
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import itertools
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from typing import Any

SCHEMA_VERSION = "1.0"
ANALYSIS_VERSION = "1"
TOOL = "skill-clarity"
MAX_FILES = 20000
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_DEPTH = 32
MAX_PAIR_COMPARISONS = 50000
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".graphify",
             ".skill-clarity", ".pytest_cache", ".mypy_cache"}
STOPWORDS = set("a an and are as at be by can for from has have how in into is it of on or that the their these this to use used using when with you your skill skills agent agents should must always never only do not".split())
DISCLAIMER = (
    "This is a disk inventory and a heuristic shortlist, not the runtime skill catalog, "
    "a conflict verdict, an exhaustive semantic audit, or a measured token/billing report. "
    "Read the source instructions and applicable conditions before recommending changes."
)


class ScanError(ValueError):
    """Invalid request or unsafe output destination."""


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def warning(code: str, path: Path | str, message: str) -> dict[str, str]:
    return {"code": code, "path": str(path), "message": message}


def resolve_input(value: str | Path) -> tuple[Path, Path, Path]:
    logical = Path(os.path.abspath(Path(value).expanduser()))
    try:
        actual = logical.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ScanError(f"Cannot resolve input {logical}: {exc}") from exc
    if actual.is_file() and logical.name == "SKILL.md":
        return logical, actual, actual.parent
    if actual.is_dir():
        return logical, actual, actual
    raise ScanError(f"Input must be a directory or a SKILL.md file: {logical}")


def _scalar(value: str) -> tuple[Any, bool]:
    """Small explicit YAML subset. Unsupported YAML is not guessed into facts."""
    value = value.strip()
    if value.startswith('"'):
        try:
            return json.loads(value), True
        except (ValueError, TypeError):
            return value, False
    if value.startswith("'"):
        if len(value) >= 2 and value.endswith("'"):
            return value[1:-1].replace("''", "'"), True
        return value, False
    if value.lower() in {"true", "false"}:
        return value.lower() == "true", True
    if value in {"null", "Null", "NULL", "~"}:
        return None, True
    if not value or value[0] in "[{}&*!" or re.search(r":\s", value):
        return value, False
    return re.split(r"\s+#", value, maxsplit=1)[0].rstrip(), True


def parse_frontmatter(text: str, path: Path) -> tuple[dict[str, Any], dict[str, tuple[int, int]], list[dict[str, str]]]:
    """Parse scalar top-level fields and YAML |/> blocks; report other syntax."""
    lines = text.splitlines()
    metadata: dict[str, Any] = {}
    locations: dict[str, tuple[int, int]] = {}
    warnings: list[dict[str, str]] = []
    if not lines or lines[0].lstrip("\ufeff").strip() != "---":
        return metadata, locations, [warning("missing_frontmatter", path, "No opening YAML frontmatter delimiter.")]
    end = next((i for i in range(1, len(lines)) if lines[i].strip() in {"---", "..."}), None)
    if end is None:
        return metadata, locations, [warning("unclosed_frontmatter", path, "Frontmatter closing delimiter is missing.")]
    i = 1
    while i < end:
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if not match:
            warnings.append(warning("unsupported_frontmatter", path, f"Unsupported YAML at line {i + 1}; not interpreted."))
            i += 1
            continue
        key, value = match.groups()
        start = i + 1
        if key in metadata:
            warnings.append(warning("duplicate_frontmatter_key", path, f"Duplicate key {key!r} at line {start}; first value retained."))
            i += 1
            continue
        block = re.fullmatch(r"([|>])([+-]?)\s*(?:#.*)?", value)
        if block:
            i += 1
            content: list[str] = []
            while i < end and (not lines[i].strip() or lines[i][0].isspace()):
                content.append(lines[i])
                i += 1
            indents = [len(x) - len(x.lstrip()) for x in content if x.strip()]
            indent = min(indents, default=0)
            clean = [x[indent:] if x.strip() else "" for x in content]
            if block[1] == "|":
                parsed = "\n".join(clean)
            else:
                # Preserve paragraph breaks; fold normal same-indent lines.
                parsed = ""
                for n, part in enumerate(clean):
                    if n:
                        previous = clean[n - 1]
                        parsed += " " if part and previous and not part.startswith(" ") and not previous.startswith(" ") else "\n"
                    parsed += part
            metadata[key] = parsed.rstrip("\n") + ("" if block[2] == "-" else "\n")
            locations[key] = (start, i)
            continue
        parsed, supported = _scalar(value)
        if supported:
            metadata[key] = parsed
        else:
            warnings.append(warning("unsupported_frontmatter", path, f"Field {key!r} at line {start} is outside the supported scalar YAML subset."))
        locations[key] = (start, start)
        i += 1
    for key in ("name", "description"):
        if not isinstance(metadata.get(key), str) or not metadata[key].strip():
            warnings.append(warning("missing_or_invalid_metadata", path, f"Missing or non-text {key}; selection hints are incomplete."))
    return metadata, locations, warnings


class Reader:
    def __init__(self) -> None:
        self.warnings: list[dict[str, str]] = []
        self.complete = True
        self.bytes_read = 0
        self.files_seen = 0
        self.cache: dict[Path, bytes | None] = {}
        self.skipped_directories: set[str] = set()
        self.omitted_files: set[str] = set()

    def omit(self, code: str, path: Path, message: str) -> None:
        self.complete = False
        self.omitted_files.add(str(path))
        self.warnings.append(warning(code, path, message))

    def read(self, path: Path) -> bytes | None:
        if path in self.cache:
            return self.cache[path]
        self.cache[path] = None
        try:
            info = path.stat()
            if not stat.S_ISREG(info.st_mode):
                self.omit("non_regular_file", path, "Not a regular file; never opened.")
                return None
            if info.st_size > MAX_FILE_BYTES or self.bytes_read + info.st_size > MAX_TOTAL_BYTES:
                self.omit("read_limit", path, "File or total byte limit reached; fingerprint coverage is incomplete.")
                return None
            with path.open("rb") as stream:
                data = stream.read(MAX_FILE_BYTES + 1)
            if len(data) > MAX_FILE_BYTES or self.bytes_read + len(data) > MAX_TOTAL_BYTES:
                self.omit("read_limit", path, "File grew beyond the read limit; excluded.")
                return None
            after = path.stat()
            if (info.st_size, info.st_mtime_ns, info.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                self.omit("changed_during_scan", path, "File changed while being read; rerun for a stable snapshot.")
                return None
            self.bytes_read += len(data)
            self.cache[path] = data
            return data
        except OSError as exc:
            self.omit("unreadable_file", path, str(exc))
            return None

    def walk(self, logical: Path, actual: Path, boundary: Path) -> list[tuple[Path, Path]]:
        results: list[tuple[Path, Path]] = []

        def visit(alias: Path, target: Path, ancestors: frozenset[Path], depth: int) -> None:
            if self.files_seen >= MAX_FILES:
                self.omit("file_limit", alias, f"Traversal limit {MAX_FILES} reached.")
                return
            self.files_seen += 1
            if depth > MAX_DEPTH:
                self.omit("depth_limit", alias, f"Traversal depth limit {MAX_DEPTH} reached.")
                return
            try:
                resolved = target.resolve(strict=True)
                if not is_within(resolved, boundary):
                    self.omit("outside_root_symlink", alias, "Target is outside this supplied root; supply it separately to include it.")
                    return
                if resolved.is_dir():
                    if resolved in ancestors:
                        self.omit("symlink_cycle", alias, "Directory cycle skipped.")
                        return
                    # Limit directory enumeration too; do not materialize millions
                    # of entries just to discover that the traversal is capped.
                    entries = list(itertools.islice(resolved.iterdir(), MAX_FILES + 1))
                    if len(entries) > MAX_FILES:
                        self.omit("directory_limit", alias, f"Directory listing exceeded {MAX_FILES} entries.")
                    for entry in sorted(entries[:MAX_FILES], key=lambda p: p.name):
                        if self.files_seen >= MAX_FILES:
                            self.omit("file_limit", alias, f"Traversal limit {MAX_FILES} reached.")
                            break
                        if entry.name in SKIP_DIRS and entry.is_dir():
                            self.skipped_directories.add(str(alias / entry.name))
                            continue
                        visit(alias / entry.name, entry, ancestors | {resolved}, depth + 1)
                else:
                    if resolved.is_file():
                        results.append((alias, resolved))
                    else:
                        self.omit("non_regular_file", alias, "Not a regular file; excluded.")
            except (OSError, RuntimeError) as exc:
                self.omit("unreadable_path", alias, str(exc))

        visit(logical, actual, frozenset(), 0)
        return results


def terms(text: str) -> set[str]:
    return {word for word in re.findall(r"[^\W_][\w-]{2,}", text.lower(), re.UNICODE) if word not in STOPWORDS}


def evidence(path: Path, lines: list[str], start: int, end: int) -> dict[str, Any]:
    return {"path": str(path), "line_start": start, "line_end": end,
            "quote": "\n".join(lines[start - 1:end])[:800]}


def reference_paths(text: str) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    for n, line in enumerate(text.splitlines(), 1):
        # Markdown local destinations and explicit relative file names in code spans.
        patterns = re.findall(r"\]\(<?([^\s)>]+)>?(?:\s+['\"].*?['\"])?\)", line)
        patterns += re.findall(r"`((?:\.\.?/|references/|scripts/|assets/|agents/)[^`]+)`", line)
        for raw in patterns:
            raw = raw.split("#", 1)[0]
            if not raw or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", raw) or raw.startswith("//"):
                continue
            if "$" in raw or "*" in raw or "\n" in raw:
                continue
            found.append((raw, n))
    return found


def scan_paths(roots: list[str | Path], candidates: list[str | Path] | None = None, max_pairs: int = 30) -> dict[str, Any]:
    """Pure read API. No snapshot or output writes. Paths are explicit scan scope."""
    if not roots:
        raise ScanError("Provide at least one installed collection root.")
    if max_pairs < 0:
        raise ScanError("max_pairs must be zero or greater.")
    installed = [resolve_input(root) for root in roots]
    incoming = [resolve_input(root) for root in (candidates or [])]
    reader = Reader()
    roots_info = [(triple, False) for triple in installed] + [(triple, True) for triple in incoming]
    boundaries = sorted({triple[2] for triple, _ in roots_info}, key=str)
    files: dict[Path, set[Path]] = {}
    candidate_files: set[Path] = set()
    installed_files: set[Path] = set()
    for (logical, actual, boundary), is_candidate in roots_info:
        # A direct SKILL.md input still fingerprints its supporting directory.
        walk_logical = logical.parent if actual.is_file() else logical
        walk_actual = actual.parent if actual.is_file() else actual
        listed = reader.walk(walk_logical, walk_actual, boundary)
        for alias, target in listed:
            files.setdefault(target, set()).add(alias)
            if alias.name == "SKILL.md" and (not actual.is_file() or target == actual):
                (candidate_files if is_candidate else installed_files).add(target)
    skill_paths = sorted(installed_files | candidate_files, key=str)
    for _, actual, _ in incoming:
        if not any(is_within(path, actual) if actual.is_dir() else path == actual for path in candidate_files):
            reader.omit("no_candidate_skills", actual, "No readable SKILL.md was discovered in this candidate.")

    inventory: list[dict[str, Any]] = []
    matching: dict[str, dict[str, Any]] = {}
    for skill_path in skill_paths:
        data = reader.read(skill_path)
        if data is None:
            continue
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            reader.omit("invalid_utf8", skill_path, "SKILL.md is not UTF-8; omitted from inventory.")
            continue
        metadata, locations, parse_warnings = parse_frontmatter(text, skill_path)
        reader.warnings.extend(parse_warnings)
        lines = text.splitlines()
        name = metadata.get("name")
        description = metadata.get("description")
        name = name.strip() if isinstance(name, str) and name.strip() else skill_path.parent.name
        description = description.strip() if isinstance(description, str) else ""
        skill_id = "skill-" + digest(str(skill_path).encode())[:16]
        skill_alias_dirs = {alias.parent for alias in files.get(skill_path, set())}
        own_files = {path for path, aliases in files.items()
                     if is_within(path, skill_path.parent)
                     or any(is_within(alias, folder) for alias in aliases for folder in skill_alias_dirs)}
        own_files.add(skill_path)
        manifest: dict[str, str] = {}
        evidence_manifest: dict[str, str] = {}
        references: list[dict[str, Any]] = []
        queue = sorted(own_files, key=str)
        visited: set[Path] = set()
        support_characters = 0
        while queue:
            file = queue.pop(0)
            if file in visited:
                continue
            visited.add(file)
            content = reader.read(file)
            if content is None:
                continue
            rel = os.path.relpath(file, skill_path.parent)
            manifest[rel] = digest(content)
            evidence_manifest[str(file)] = digest(content)
            try:
                content_text = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                continue
            if file != skill_path:
                support_characters += len(content_text)
            if file.suffix.lower() not in {".md", ".mdx"}:
                continue
            for raw, line_num in reference_paths(content_text):
                target = file.parent / raw
                try:
                    resolved = target.resolve(strict=True)
                    if not any(is_within(resolved, boundary) for boundary in boundaries):
                        reader.omit("outside_root_reference", target, "Referenced file lies outside supplied roots; not read or hashed.")
                        references.append({"from": rel, "line": line_num, "target": raw, "status": "outside_scope"})
                        continue
                    if resolved.is_file():
                        references.append({"from": rel, "line": line_num, "target": raw, "status": "hashed"})
                        if resolved not in visited:
                            queue.append(resolved)
                    elif resolved.is_dir():
                        references.append({"from": rel, "line": line_num, "target": raw, "status": "hashed_directory"})
                        manifest["directory-reference:" + rel + ":" + raw] = "directory"
                        queue.extend(path for path in sorted(files, key=str)
                                     if is_within(path, resolved) and path not in visited)
                except (OSError, RuntimeError):
                    references.append({"from": rel, "line": line_num, "target": raw, "status": "unresolved"})
                    reader.warnings.append(warning("unresolved_reference", file, f"Local reference at line {line_num} could not be resolved: {raw}"))
                    # A broken link is inventoried, but no existing content is silently lost.
                    manifest["missing-reference:" + rel + ":" + raw] = "missing"
        fingerprint = digest(canonical_json(manifest))
        ev = [evidence(skill_path, lines, *locations[key]) for key in ("name", "description") if key in locations]
        broad = []
        for number, line in enumerate(lines, 1):
            if re.search(r"\b(every (?:prompt|request|turn|task|session)|always (?:use|invoke|run|load)|before (?:any|every|all))\b", line, re.I):
                broad.append(evidence(skill_path, lines, number, number))
        if broad:
            reader.warnings.append(warning("broad_activation_language", skill_path, "Broad activation language needs contextual review; text alone does not prove runtime activation."))
        selected_metadata = {key: metadata[key] for key in ("name", "description", "disable-model-invocation", "user-invocable", "allowed-tools", "compatibility", "version") if key in metadata}
        record = {
            "id": skill_id, "name": name, "description": description, "path": str(skill_path),
            "aliases": sorted(str(alias) for alias in files.get(skill_path, set()) if alias != skill_path),
            "fingerprint": fingerprint, "metadata": selected_metadata,
            "activation_clues": {"declared": {key: metadata[key] for key in ("disable-model-invocation", "user-invocable") if key in metadata},
                                 "broad_language": broad[:8], "runtime_status": "unknown"},
            "approx_text_cost": {"method": "ceil(characters/4); rough size proxy only",
                                 "catalog_characters": len(name) + len(description),
                                 "catalog_token_estimate": math.ceil((len(name) + len(description)) / 4),
                                 "skill_characters": len(text), "skill_token_estimate": math.ceil(len(text) / 4),
                                 "support_characters": support_characters, "is_runtime_measurement": False},
            "is_candidate": skill_path in candidate_files, "is_installed_input": skill_path in installed_files,
            "scope": "unknown", "evidence": ev, "references": references,
            "fingerprinted_files": len(manifest),
            "fingerprint_manifest": [{"path": path, "sha256": sha} for path, sha in sorted(evidence_manifest.items())],
        }
        inventory.append(record)
        matching[skill_id] = {"description": terms(name + " " + description), "body": terms(text), "broad": broad}
        if record["is_candidate"] and record["is_installed_input"]:
            reader.warnings.append(warning("candidate_already_present", skill_path, "Candidate resolves to a skill already in the installed input; no second copy invented."))

    # Bound comparison work and memory separately from the output cap.
    # Candidate mode never iterates through old/old combinations.
    pair_heap: list[tuple[float, str, dict[str, Any]]] = []
    count = len(inventory)
    if incoming:
        fresh = [row for row in inventory if row["is_candidate"]]
        old = [row for row in inventory if not row["is_candidate"]]
        combinations = itertools.chain(itertools.product(fresh, old), itertools.combinations(fresh, 2))
        eligible = len(fresh) * len(old) + len(fresh) * (len(fresh) - 1) // 2
    else:
        combinations = itertools.combinations(inventory, 2)
        eligible = count * (count - 1) // 2
    evaluated = 0
    shortlisted = 0
    for a, b in itertools.islice(combinations, MAX_PAIR_COMPARISONS if max_pairs else 0):
        evaluated += 1
        ta, tb = matching[a["id"]], matching[b["id"]]
        left, right = ta["description"], tb["description"]
        common = left & right
        union = left | right
        similarity = len(common) / len(union) if union else 0.0
        body_common = ta["body"] & tb["body"]
        body_union = ta["body"] | tb["body"]
        body_similarity = len(body_common) / len(body_union) if body_union else 0.0
        reasons = []
        if a["fingerprint"] == b["fingerprint"]:
            reasons.append("identical_fingerprinted_content")
        if a["name"].casefold() == b["name"].casefold():
            reasons.append("same_declared_or_fallback_name")
        if similarity >= 0.15 and common:
            reasons.append("shared_description_vocabulary")
        if body_similarity >= 0.22 and len(body_common) >= 4:
            reasons.append("shared_instruction_vocabulary")
        if ta["broad"] or tb["broad"]:
            reasons.append("broad_activation_review")
        if not reasons:
            continue
        ids = sorted((a["id"], b["id"]))
        pair_id = "pair-" + digest(canonical_json(ids))[:16]
        pair_fingerprint = digest(canonical_json({"analysis_version": ANALYSIS_VERSION,
                                                 "skills": sorted([(a["id"], a["fingerprint"]), (b["id"], b["fingerprint"])])}))
        rank = (100 if "identical_fingerprinted_content" in reasons else 0) + (50 if "same_declared_or_fallback_name" in reasons else 0) + similarity + body_similarity
        pair = {"id": pair_id, "a": a["id"], "b": b["id"], "fingerprint": pair_fingerprint,
                      "reasons": reasons, "lexical_similarity": round(similarity, 4),
                      "body_lexical_similarity": round(body_similarity, 4),
                      "shared_terms": sorted(common)[:12], "evidence": (a["evidence"] + b["evidence"] + ta["broad"][:1] + tb["broad"][:1]),
                      "status": "needs_review"}
        shortlisted += 1
        if max_pairs:
            entry = (rank, pair_id, pair)
            if len(pair_heap) < max_pairs:
                heapq.heappush(pair_heap, entry)
            elif entry[:2] > pair_heap[0][:2]:
                heapq.heapreplace(pair_heap, entry)
    selected = [entry[2] for entry in sorted(pair_heap, key=lambda entry: (-entry[0], entry[1]))]
    if not max_pairs and eligible:
        reader.warnings.append(warning("pair_search_skipped", "", "Pair selection was explicitly skipped (--max-pairs 0); inventory and source fingerprints only."))
    elif evaluated < eligible:
        reader.warnings.append(warning("pair_comparison_limit", "", f"Compared {evaluated} of {eligible} eligible pairs. Narrow the roots or use candidate mode; the unexamined pairs may contain additional findings."))
    if shortlisted > max_pairs:
        reader.warnings.append(warning("pair_limit", "", f"Returned {max_pairs} of {shortlisted} shortlisted pairs; increase --max-pairs to inspect the rest."))
    warnings = list({(w["code"], w["path"], w["message"]): w for w in reader.warnings}.values())
    context = {"roots": sorted(str(triple[1]) for triple in installed),
               "candidates": sorted(str(triple[1]) for triple in incoming)}
    return {
        "tool": TOOL, "kind": "scan", "schema_version": SCHEMA_VERSION, "analysis_version": ANALYSIS_VERSION,
        "scan_context": context, "inventory": inventory, "candidate_pairs": selected,
        "coverage": {"complete": reader.complete, "skill_count": len(inventory), "eligible_pairs": eligible,
                     "shortlisted_pairs": shortlisted, "returned_pairs": len(selected),
                     "omitted_pairs": shortlisted - len(selected), "not_shortlisted_pairs": evaluated - shortlisted,
                     "evaluated_pairs": evaluated, "not_evaluated_pairs": eligible - evaluated,
                     "pair_search_complete": evaluated == eligible,
                     "semantic_analysis": False, "read_bytes": reader.bytes_read,
                     "omitted_files": sorted(reader.omitted_files), "skipped_directories": sorted(reader.skipped_directories),
                     "limits": {"files": MAX_FILES, "bytes_per_file": MAX_FILE_BYTES,
                                "total_bytes": MAX_TOTAL_BYTES, "depth": MAX_DEPTH, "pairs": max_pairs,
                                "pair_comparisons": MAX_PAIR_COMPARISONS}},
        "warnings": warnings, "disclaimer": DISCLAIMER,
    }


def validate_destination(value: str | Path, inputs: list[str | Path], expected_kind: str) -> Path:
    logical = Path(os.path.abspath(Path(value).expanduser()))
    if logical.is_symlink():
        raise ScanError(f"Refusing a symlink output destination: {logical}")
    target = logical.resolve()
    for source in inputs:
        _, actual, boundary = resolve_input(source)
        if target == actual or is_within(target, boundary):
            raise ScanError(f"Output/state must be outside inspected input directories: {target}")
    if target.exists():
        if not target.is_file():
            raise ScanError(f"Output destination is not a regular file: {target}")
        try:
            if target.stat().st_size > MAX_FILE_BYTES:
                raise ScanError(f"Existing destination is too large to validate: {target}")
            value = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ScanError(f"Refusing to overwrite a file not produced by Skill Clarity: {target}") from exc
        if not isinstance(value, dict) or value.get("tool") != TOOL or value.get("kind") != expected_kind:
            raise ScanError(f"Refusing to overwrite unrelated content: {target}")
    return target


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise


def apply_state(report: dict[str, Any], path: Path | None) -> None:
    current = {row["id"]: row["fingerprint"] for row in report["inventory"]}
    signature = digest(canonical_json({"context": report["scan_context"], "analysis_version": ANALYSIS_VERSION}))
    previous: dict[str, str] = {}
    status = "initial"
    if path and path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        if old.get("schema_version") != SCHEMA_VERSION:
            raise ScanError(f"Unsupported snapshot schema in {path}; preserve it and choose a new --state path.")
        if old.get("signature") != signature:
            status = "invalidated"
        else:
            previous = old.get("fingerprints", {})
            if not isinstance(previous, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in previous.items()):
                raise ScanError(f"Invalid snapshot fingerprints in {path}.")
            status = "compared"
    complete = report["coverage"]["complete"]
    report["changes"] = {
        "status": status if complete else "not_saved_incomplete",
        "new": sorted(set(current) - set(previous)),
        "changed": sorted(key for key in current.keys() & previous.keys() if current[key] != previous[key]),
        "removed": sorted(set(previous) - set(current)) if complete else [],
        "unchanged": sorted(key for key in current.keys() & previous.keys() if current[key] == previous[key]),
        "persisted": bool(path and complete),
        "note": "Unchanged files do not resolve review findings. Candidate pairs remain pending until reviewed.",
    }
    if path and complete:
        atomic_write(path, {"tool": TOOL, "kind": "state", "schema_version": SCHEMA_VERSION,
                            "analysis_version": ANALYSIS_VERSION, "signature": signature,
                            "scan_context": report["scan_context"], "fingerprints": current})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example: python3 scan.py scan ~/.agents/skills --candidate ./new-skill --state ./audit/state.json\n"
               "Explicit roots may be symlinks. Nested links outside a root are reported and not followed.\n"
               "State/output must be outside inspected directories. Text size estimates are not billing.\n"
               "Exit 0: complete filesystem scan; 1: incomplete coverage; 2: invalid request or output error.")
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("scan", help="Inventory explicit directories and shortlist pairs for human/agent review.")
    scan.add_argument("roots", nargs="+", help="Installed skill directory, collection directory, or SKILL.md.")
    scan.add_argument("--candidate", action="append", default=[], metavar="PATH", help="Incoming skill or pack; repeatable. Does not install anything.")
    scan.add_argument("--state", help="Explicit snapshot path outside inspected roots; updated only after complete scans.")
    scan.add_argument("--output", help="Full JSON output path; prints only a compact summary to stdout. Default: full JSON on stdout.")
    scan.add_argument("--max-pairs", type=int, default=30, help="Maximum returned shortlist pairs (default 30); zero inventories only.")
    args = parser.parse_args(argv)
    try:
        sources = args.roots + args.candidate
        # Validate destinations before any read/write work; preserve source inputs.
        state_path = validate_destination(args.state, sources, "state") if args.state else None
        output_path = validate_destination(args.output, sources, "scan") if args.output else None
        if state_path and output_path and state_path == output_path:
            raise ScanError("--state and --output must be different files.")
        report = scan_paths(args.roots, args.candidate, args.max_pairs)
        apply_state(report, state_path)
        if output_path:
            atomic_write(output_path, report)
            coverage = report["coverage"]
            print(json.dumps({
                "output": str(output_path),
                "skill_count": coverage["skill_count"],
                "filesystem_complete": coverage["complete"],
                "pair_search_complete": coverage["pair_search_complete"],
                "returned_pairs": coverage["returned_pairs"],
                "omitted_pairs": coverage["omitted_pairs"],
                "not_evaluated_pairs": coverage["not_evaluated_pairs"],
                "changes": {key: len(report["changes"][key])
                            for key in ("new", "changed", "removed", "unchanged")},
                "warnings": len(report["warnings"]),
            }, ensure_ascii=False))
        else:
            json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
            sys.stdout.write("\n")
        return 0 if report["coverage"]["complete"] else 1
    except (ScanError, OSError, ValueError) as exc:
        print(json.dumps({"tool": TOOL, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

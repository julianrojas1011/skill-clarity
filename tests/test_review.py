"""Evidence freshness and safe rendering checks for saved skill reviews."""
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


BASE = Path(__file__).resolve().parents[1]
SCANNER = BASE / "skills" / "skill-clarity" / "scripts" / "scan.py"
REVIEW = BASE / "skills" / "skill-clarity" / "scripts" / "review.py"


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "collection"
        self.root.mkdir()
        self.folders = []
        for folder, name, radius in (("first", "product-style", 8), ("second", "button-polish", 24)):
            path = self.root / folder
            path.mkdir()
            (path / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Style buttons in the existing product.\n---\n\n# Rules\n\nUse a {radius}px radius for every button.\n\nSee [details](references/details.md).\n")
            (path / "references").mkdir()
            (path / "references" / "details.md").write_text("This contract applies to the existing product.\n")
            self.folders.append(path)
        process = subprocess.run([sys.executable, str(SCANNER), "scan", str(self.root)], capture_output=True, text=True, timeout=20)
        self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
        self.scan = json.loads(process.stdout)
        self.scan_path = self.base / "scan.json"
        self.scan_path.write_text(process.stdout)
        self.review_path = self.base / "review.json"
        skills = self.scan["inventory"]
        self.document = {
            "tool": "skill-clarity", "kind": "review", "schema_version": "1.0",
            "environment": "Synthetic local fixtures; runtime activation not observed.",
            "findings": [{
                "id": "button-radius",
                "skills": [{"id": s["id"], "fingerprint": s["fingerprint"]} for s in skills],
                "relationship": "contradiction",
                "scenario": "Both skills guide the same existing product button change.",
                "confidence": "text-supported",
                "recommendation": "Choose one radius contract for this product and scope the other skill to prototypes.",
                "preserved_value": "Keep product consistency and retain polish guidance for prototypes.",
                "evidence": [{"skill_id": s["id"], "path": "SKILL.md", "line_start": 8, "line_end": 8,
                              "quote": Path(s["path"]).read_text().splitlines()[7]} for s in skills],
            }],
        }
        self.write_review()

    def write_review(self):
        self.review_path.write_text(json.dumps(self.document))

    def execute(self, command="validate", extra=(), expected=0):
        process = subprocess.run([sys.executable, str(REVIEW), command, "--scan", str(self.scan_path),
                                  "--review", str(self.review_path), *map(str, extra)], capture_output=True, text=True, timeout=20)
        self.assertEqual(process.returncode, expected, process.stderr + process.stdout)
        return process

    def test_valid_evidence_passes_without_mutation(self):
        before = {path: path.read_bytes() for path in self.base.rglob("*") if path.is_file()}
        result = self.execute()
        self.assertIsInstance(json.loads(result.stdout), dict)
        after = {path: path.read_bytes() for path in self.base.rglob("*") if path.is_file()}
        self.assertEqual(before, after)

    def test_changed_reference_invalidates_saved_finding(self):
        (self.folders[0] / "references" / "details.md").write_text("This contract now applies only to prototypes.\n")
        self.execute(expected=1)

    def test_changed_skill_invalidates_saved_finding(self):
        path = self.folders[0] / "SKILL.md"
        path.write_text(path.read_text().replace("8px", "24px"))
        self.execute(expected=1)

    def test_invented_quote_is_rejected(self):
        self.document["findings"][0]["evidence"][0]["quote"] = "Use a 100px radius for every button."
        self.write_review()
        self.execute(expected=1)

    def test_wrong_line_is_rejected(self):
        self.document["findings"][0]["evidence"][0]["line_start"] = 2
        self.document["findings"][0]["evidence"][0]["line_end"] = 2
        self.write_review()
        self.execute(expected=1)

    def test_foreign_unfingerprinted_evidence_is_rejected(self):
        evidence = self.document["findings"][0]["evidence"][0]
        evidence["path"] = "../second/SKILL.md"
        evidence["quote"] = (self.folders[1] / "SKILL.md").read_text().splitlines()[7]
        self.write_review()
        self.execute(expected=1)

    def test_missing_source_skill_is_rejected(self):
        (self.folders[0] / "SKILL.md").unlink()
        self.execute(expected=1)

    def test_unknown_fingerprint_is_rejected(self):
        self.document["findings"][0]["skills"][0]["fingerprint"] = "0" * 64
        self.write_review()
        self.execute(expected=1)

    def test_missing_recommendation_is_rejected(self):
        del self.document["findings"][0]["recommendation"]
        self.write_review()
        self.execute(expected=1)

    def test_invalid_relationship_is_rejected(self):
        self.document["findings"][0]["relationship"] = "universal-winner"
        self.write_review()
        self.execute(expected=1)

    def test_html_escapes_untrusted_review_text(self):
        self.document["findings"][0]["recommendation"] = '<script>alert("untrusted")</script> Keep both with explicit scope.'
        self.write_review()
        output = self.base / "report.html"
        self.execute("render", ("--format", "html", "--output", output))
        html = output.read_text()
        self.assertNotIn('<script>alert("untrusted")</script>', html)
        self.assertIn("&lt;script&gt;", html)

    def test_render_preserves_unrelated_existing_file(self):
        output = self.base / "report.html"
        output.write_text("User-authored content, preserve me.\n")
        self.execute("render", ("--format", "html", "--output", output), expected=2)
        self.assertEqual(output.read_text(), "User-authored content, preserve me.\n")

    def test_render_refuses_input_overwrite(self):
        original = self.review_path.read_bytes()
        self.execute("render", ("--format", "markdown", "--output", self.review_path), expected=2)
        self.assertEqual(self.review_path.read_bytes(), original)

    def test_render_refuses_output_symlink(self):
        target = self.base / "personal.html"
        target.write_text("Do not change.\n")
        output = self.base / "report.html"
        output.symlink_to(target)
        self.execute("render", ("--format", "html", "--output", output), expected=2)
        self.assertEqual(target.read_text(), "Do not change.\n")

    def test_stale_source_does_not_mask_invalid_review_structure(self):
        (self.folders[0] / "references" / "details.md").write_text("Changed supporting rules.\n")
        del self.document["findings"][0]["recommendation"]
        self.write_review()
        output = self.base / "report.html"
        self.execute("render", ("--format", "html", "--output", output), expected=2)
        self.assertFalse(output.exists())

    def test_forged_old_manifest_cannot_authorize_foreign_evidence(self):
        foreign = self.base / "private-note.md"
        foreign.write_text("PRIVATE MARKER SHOULD NOT BE READ AS EVIDENCE\n")
        first = self.scan["inventory"][0]
        first["fingerprint_manifest"].append({"path": str(foreign.resolve()),
                                               "sha256": hashlib.sha256(foreign.read_bytes()).hexdigest()})
        self.scan_path.write_text(json.dumps(self.scan))
        evidence = self.document["findings"][0]["evidence"][0]
        evidence.update(path="../../private-note.md", line_start=1, line_end=1,
                        quote="PRIVATE MARKER SHOULD NOT BE READ AS EVIDENCE")
        self.write_review()
        process = self.execute(expected=1)
        self.assertNotIn("PRIVATE MARKER", process.stdout)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO test requires POSIX")
    def test_fifo_json_is_rejected_without_blocking(self):
        fifo = self.base / "scan-pipe"
        os.mkfifo(fifo)
        process = subprocess.run([sys.executable, str(REVIEW), "validate", "--scan", str(fifo),
                                  "--review", str(self.review_path)], capture_output=True, text=True, timeout=3)
        self.assertEqual(process.returncode, 2, process.stdout + process.stderr)
        self.assertIn("regular file", process.stderr)

    def test_markdown_renders_html_and_images_as_literal_text(self):
        self.document["findings"][0]["recommendation"] = '<img src="https://example.invalid/pixel"> ![track](https://example.invalid/pixel)'
        self.write_review()
        output = self.base / "report.md"
        self.execute("render", ("--format", "markdown", "--output", output))
        markdown = output.read_text()
        self.assertNotIn('<img src=', markdown)
        self.assertIn("&lt;img", markdown)
        self.assertNotIn("![track](", markdown)
        self.assertIn(r"\!\[track\]\(", markdown)

    def test_malformed_nested_scan_schema_returns_clean_input_error(self):
        self.scan["scan_context"] = []
        self.scan_path.write_text(json.dumps(self.scan))
        process = self.execute(expected=2)
        self.assertNotIn("Traceback", process.stderr)
        self.assertIsInstance(json.loads(process.stderr), dict)


if __name__ == "__main__":
    unittest.main()

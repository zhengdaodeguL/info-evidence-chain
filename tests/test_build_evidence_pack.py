"""Regression tests for portable evidence packs; all assets use temporary folders."""

import hashlib
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit

from PIL import Image


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_evidence_pack.py"
SPEC = importlib.util.spec_from_file_location("build_evidence_pack", SCRIPT)
PACK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACK)


class BuildEvidencePackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="info-evidence-pack-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "输入 原图.png"
        Image.new("RGB", (160, 100), "#ECF2FA").save(self.source)
        self.annotated = self.root / "中文标注.png"
        Image.new("RGB", (300, 100), "#ECF2FA").save(self.annotated)
        self.text = self.root / "原文.txt"
        self.text.write_text("示例原文：糖含量与每 100 mL 的标签基准。", encoding="utf-8")
        self.annotations = self.root / "坐标.json"
        self.annotations.write_text('{"boxes": [{"id": "K1", "label": "中文关键点"}]}', encoding="utf-8")
        self.manifest = self.root / "manifest-input.json"
        self.output = self.root / "发布证据包"
        self.entry = {
            "evidence_id": "E-001", "title": "中文标准页面", "query": "营养 标签",
            "captured_at": "2026-10-30T09:00:00+09:00", "url": "https://example.org/search?q=label&lang=zh",
            "screenshot_path": self.source.name, "annotated_path": self.annotated.name,
            "annotations_path": self.annotations.name, "text_path": self.text.name,
            "excerpt": "示例逐字摘录", "verification_status": "auto_verified",
            "verification_checks": [{"check": "text_match", "passed": True}],
        }

    def write_manifest(self, entries=None, **extra):
        payload = {"title": "中文证据包", "scope": "合成测试，不是真实研究证据",
                   "evidence": [self.entry] if entries is None else entries}
        payload.update(extra)
        self.manifest.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return payload

    def test_preserves_original_bytes_and_hashes_every_copied_asset(self):
        self.write_manifest()
        original_manifest = self.manifest.read_bytes()
        original_assets = {path: path.read_bytes() for path in [self.source, self.annotated, self.text, self.annotations]}
        result = PACK.build(self.manifest, self.output)
        packed = json.loads((self.output / "manifest.json").read_text(encoding="utf-8"))
        entry = packed["evidence"][0]
        for key, path in [("screenshot_path", self.source), ("annotated_path", self.annotated),
                          ("text_path", self.text), ("annotations_path", self.annotations)]:
            self.assertEqual(path.read_bytes(), original_assets[path])
            self.assertEqual((self.output / entry[key]).read_bytes(), original_assets[path])
            self.assertEqual(entry["sha256"][key], hashlib.sha256(original_assets[path]).hexdigest())
            self.assertFalse(Path(entry[key]).is_absolute())
        self.assertEqual(self.manifest.read_bytes(), original_manifest)
        self.assertEqual(packed["summary"], {"auto_verified": 1})
        self.assertEqual(Path(result["index_path"]), (self.output / "index.html").resolve())

    def test_relative_links_resolve_and_chinese_survives_utf8(self):
        self.write_manifest()
        PACK.build(self.manifest, self.output)
        html = (self.output / "index.html").read_text(encoding="utf-8")
        self.assertIn("中文证据包", html)
        self.assertIn("示例逐字摘录", html)
        for link in re.findall(r'(?:href|src)="([^"]+)"', html):
            if urlsplit(link).scheme:
                continue
            self.assertFalse(Path(unquote(link)).is_absolute())
            self.assertTrue((self.output / unquote(link)).is_file(), link)

    def test_html_escapes_content_attributes_and_log(self):
        attack = '\"><script>alert("x")</script><img src=x onerror=alert(1)>'
        self.entry.update(title=attack, excerpt=attack, query=attack, finding=attack,
                          locator=attack, url='javascript:alert("x")')
        self.write_manifest(title=attack, scope=attack,
                            search_log=[{"at": attack, "action": attack, "query": attack, "outcome": attack}])
        PACK.build(self.manifest, self.output)
        html = (self.output / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('<script>alert("x")</script>', html)
        self.assertNotIn('<img src=x onerror=alert(1)>', html)
        self.assertNotIn('href="javascript:', html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&quot;", html)

    def test_embedded_template_tokens_are_not_interpreted(self):
        self.entry["excerpt"] = "__TITLE__ __SCOPE__ __CARDS__ __LOG__"
        self.write_manifest()
        PACK.build(self.manifest, self.output)
        html = (self.output / "index.html").read_text(encoding="utf-8")
        self.assertIn("__TITLE__ __SCOPE__ __CARDS__ __LOG__", html)

    def test_rejects_nonempty_output_without_touching_it(self):
        self.write_manifest()
        self.output.mkdir()
        marker = self.output / "existing.txt"
        marker.write_text("保留已有包", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "new or empty"):
            PACK.build(self.manifest, self.output)
        self.assertEqual(marker.read_text(encoding="utf-8"), "保留已有包")
        self.assertEqual(list(self.output.iterdir()), [marker])

    def test_missing_image_rejects_before_output_is_created(self):
        self.entry["screenshot_path"] = "不存在.png"
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "Missing screenshot_path"):
            PACK.build(self.manifest, self.output)
        self.assertFalse(self.output.exists())

    def test_duplicate_ids_reject_before_output_is_created(self):
        self.write_manifest(entries=[self.entry, dict(self.entry)])
        with self.assertRaisesRegex(ValueError, "unique nonempty"):
            PACK.build(self.manifest, self.output)
        self.assertFalse(self.output.exists())

    def test_unknown_status_rejects_before_copying_assets(self):
        self.entry["verification_status"] = "misspelled-status"
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "Unknown verification_status"):
            PACK.build(self.manifest, self.output)
        self.assertFalse(self.output.exists(), "Invalid input must not leave a non-retryable partial pack")

    def test_reader_can_find_conclusion_limits_and_pending_work(self):
        self.entry.update(verification_status="needs_review", review_reason="缺少实施日期原文")
        self.write_manifest(conclusions=["页面列出该标准 <不等于已生效>"], limitations=["不能由查无推定不存在"])
        PACK.build(self.manifest, self.output)
        rendered = (self.output / "index.html").read_text(encoding="utf-8")
        overview = rendered.split('<label for="filter">')[0]
        self.assertIn("缺少实施日期原文", overview)
        self.assertIn("不能由查无推定不存在", overview)
        self.assertIn("&lt;不等于已生效&gt;", overview)
        packed = json.loads((self.output / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(packed["summary"], {"needs_review": 1})

    def test_bad_conclusions_shape_does_not_leave_partial_output(self):
        self.write_manifest(conclusions="should be a list")
        with self.assertRaisesRegex(ValueError, "array of strings"):
            PACK.build(self.manifest, self.output)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()

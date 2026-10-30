"""Regression tests for evidence-linked automation and human-review boundaries."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "score_confidence.py"
SPEC = importlib.util.spec_from_file_location("score_confidence", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def observed():
    return {
        "claim_type": "observed", "source_tier": "P1",
        "raw_material": True, "exact_locator": True,
        "evidence": [
            {"evidence_id": "E-PAGE", "path": "raw/page.png"},
            {"evidence_id": "E-TEXT", "path": "extracted/text.json"},
        ],
        "verification_checks": [
            {"check_id": "V-GROUND", "method": "grounded", "passed": True, "evidence_refs": ["E-PAGE"]},
            {"check_id": "V-MATCH", "method": "quote_match", "passed": True, "evidence_refs": ["E-PAGE", "E-TEXT"]},
        ],
    }


class EvidenceScoreTests(unittest.TestCase):
    def test_observation_can_be_high_without_human(self):
        result = MODULE.score(observed())
        self.assertEqual((result["level"], result["review_status"]), ("high", "auto_verified"))
        self.assertEqual(result["review_reasons"], [])

    def test_self_reported_auto_boolean_has_no_effect(self):
        claim = observed()
        claim.pop("verification_checks")
        claim["auto_verified"] = True
        result = MODULE.score(claim)
        self.assertEqual(result["review_status"], "needs_review")
        self.assertNotEqual(result["level"], "high")

    def test_unknown_evidence_reference_cannot_pass(self):
        claim = observed()
        claim["verification_checks"][1]["evidence_refs"] = ["E-INVENTED"]
        self.assertNotEqual(MODULE.score(claim)["level"], "high")

    def test_evidence_record_needs_a_real_locator(self):
        claim = observed()
        claim["evidence"][0].pop("path")
        self.assertNotEqual(MODULE.score(claim)["level"], "high")

    def test_one_grounding_check_is_insufficient(self):
        claim = observed()
        claim["verification_checks"].pop()
        self.assertEqual(MODULE.score(claim)["review_status"], "needs_review")

    def test_duplicate_check_id_is_an_exception(self):
        claim = observed()
        claim["verification_checks"][1]["check_id"] = "V-GROUND"
        self.assertNotEqual(MODULE.score(claim)["level"], "high")

    def test_unrecognized_method_cannot_pass(self):
        claim = observed()
        claim["verification_checks"][1]["method"] = "model_feels_sure"
        self.assertNotEqual(MODULE.score(claim)["level"], "high")

    def test_failed_check_overrides_human_verified(self):
        claim = observed()
        claim["human_verified"] = True
        claim["verification_checks"][1]["passed"] = False
        result = MODULE.score(claim)
        self.assertEqual((result["level"], result["review_status"]), ("low", "needs_review"))

    def test_unknown_result_is_not_a_truthy_string(self):
        claim = observed()
        claim["verification_checks"][1]["passed"] = "true"
        self.assertNotEqual(MODULE.score(claim)["level"], "high")

    def test_unknown_input_field_prevents_high(self):
        claim = observed()
        claim["unknown_fields"] = ["net_content"]
        self.assertNotEqual(MODULE.score(claim)["level"], "high")

    def test_unknown_boolean_does_not_hide_behind_other_valid_checks(self):
        claim = observed()
        claim["independent_crosscheck"] = "unknown"
        self.assertNotEqual(MODULE.score(claim)["level"], "high")

    def test_malformed_method_is_reported_instead_of_crashing(self):
        claim = observed()
        claim["verification_checks"][1]["method"] = ["quote_match"]
        self.assertEqual(MODULE.score(claim)["review_status"], "needs_review")

    def test_human_verification_does_not_clear_conflict(self):
        claim = observed()
        claim.update(human_verified=True, unresolved_conflict=True)
        self.assertEqual(MODULE.score(claim)["level"], "low")

    def test_normative_claim_requires_effective_and_applicable_a1(self):
        claim = observed()
        claim.update(claim_type="normative", source_tier="A1", effective_at_claim_time=True, scope_applicable=True)
        self.assertEqual(MODULE.score(claim)["level"], "high")
        for key, value in (("effective_at_claim_time", False), ("scope_applicable", "unknown"), ("source_tier", "P1")):
            variant = dict(claim, **{key: value})
            self.assertFalse(MODULE.score(variant)["gate_passed"])

    def test_negative_search_is_not_noncompliance_evidence(self):
        claim = observed()
        claim.update(claim_type="normative", source_tier="A1", effective_at_claim_time=True, scope_applicable=True, negative_search_only=True)
        self.assertFalse(MODULE.score(claim)["gate_passed"])

    def test_legacy_human_observation_is_accepted(self):
        claim = {"claim_type": "observed", "source_tier": "P1", "raw_material": True,
                 "url": "https://example.org/label", "exact_locator": True, "human_verified": True}
        self.assertEqual(MODULE.score(claim)["review_status"], "human_verified")

    def test_computation_requires_formula_recalculation(self):
        claim = observed()
        claim.update(claim_type="computed", complete_inputs=True, reproducible_formula=True)
        self.assertEqual(MODULE.score(claim)["review_status"], "needs_review")
        claim["verification_checks"][1]["method"] = "formula_recalculation"
        self.assertEqual(MODULE.score(claim)["level"], "high")
        claim["complete_inputs"] = False
        self.assertNotEqual(MODULE.score(claim)["level"], "high")

    def test_interpretation_needs_human(self):
        claim = observed()
        claim.update(claim_type="interpretive", source_ids=["S-001"], premises=["明确的前提"])
        self.assertEqual(MODULE.score(claim)["review_status"], "needs_review")

    def test_strong_allegation_and_dispute_need_review(self):
        for key in ("strong_allegation", "interpretation_disputed"):
            claim = observed()
            claim.update(human_verified=True, **{key: True})
            result = MODULE.score(claim)
            self.assertEqual(result["review_status"], "needs_review")
            self.assertNotEqual(result["level"], "high")

    def test_extraction_agreement_needs_two_evidence_ids(self):
        claim = observed()
        claim["verification_checks"][1].update(method="extraction_agreement", evidence_refs=["E-TEXT"])
        self.assertNotEqual(MODULE.score(claim)["level"], "high")

    def test_cli_preserves_array_support(self):
        process = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps([observed()]),
                                 text=True, encoding="utf-8", capture_output=True, check=True)
        self.assertEqual(json.loads(process.stdout)[0]["review_status"], "auto_verified")


if __name__ == "__main__":
    unittest.main()

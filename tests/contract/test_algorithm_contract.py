"""QA contract tests for ALGO-01 (T-ALG-01), written from the QA side.

John's unit tests (backend/algorithms/algo01/tests) check how the algorithm
works inside. These tests check what other modules rely on: that every
output follows the §02.2 Recommendation contract and the team safety rules,
and that the saved example outputs still match the real algorithm.
"""
import copy
import json
import unittest
from pathlib import Path

from backend.algorithms.algo01.raid0_policy import evaluate_raid0_policy

ALGO_FIXTURES = Path(__file__).resolve().parents[2] / "backend" / "algorithms" / "algo01" / "tests" / "fixtures"
CASES = ("d2-temp-valid", "d2-temp-none", "d2-advisory-monitoring-only")

# §02.2 Recommendation record: field -> allowed types
RECOMMENDATION_FIELDS = {
    "recommendation_id": (str,),
    "mode": (str,),
    "action": (str,),
    "file_id": (str, type(None)),
    "source_device_id": (str, type(None)),
    "target_device_id": (str, type(None)),
    "reason": (str,),
    "created_at_utc": (str,),
    "requires_approval": (bool,),
    "estimated_benefit": (dict, type(None)),
    "constraints": (list,),
}


def load_case(name):
    return json.loads((ALGO_FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def load_saved_output(name):
    return json.loads((ALGO_FIXTURES / f"{name}-output.json").read_text(encoding="utf-8"))


class Algo01ContractTests(unittest.TestCase):

    def check_contract(self, records, devices):
        media = {d["device_id"]: d["media_type"] for d in devices}
        self.assertIsInstance(records, list)
        self.assertGreater(len(records), 0, "ALGO-01 must return at least a 'none' record")
        for rec in records:
            self.assertEqual(set(rec), set(RECOMMENDATION_FIELDS), "must have exactly the 11 §02.2 fields")
            for field, allowed in RECOMMENDATION_FIELDS.items():
                self.assertIsInstance(rec[field], allowed, field)
            self.assertEqual(rec["mode"], "raid0")
            self.assertIn(rec["action"], {"move", "none"})
            self.assertTrue(rec["created_at_utc"].endswith("Z"), "timestamps must be UTC")
            # Never claim a speed-up that was not benchmarked
            self.assertIsNone(rec["estimated_benefit"])
            if rec["action"] == "move":
                self.assertIs(rec["requires_approval"], True, "a move must always need user approval")
                self.assertEqual(media[rec["source_device_id"]], "hdd")
                self.assertEqual(media[rec["target_device_id"]], "ssd")
            else:
                self.assertIs(rec["requires_approval"], False, "'none' proposes nothing to approve")
                self.assertIsNone(rec["file_id"])
                self.assertIsNone(rec["source_device_id"])
                self.assertIsNone(rec["target_device_id"])

    def test_saved_example_outputs_still_match_algorithm(self):
        for name in CASES:
            with self.subTest(case=name):
                self.assertEqual(evaluate_raid0_policy(**load_case(name)), load_saved_output(name))

    def test_every_example_output_follows_contract(self):
        for name in CASES:
            with self.subTest(case=name):
                data = load_case(name)
                self.check_contract(evaluate_raid0_policy(**data), data["devices"])

    def test_no_ssd_gives_safe_none(self):
        data = load_case("d2-temp-valid")
        for device in data["devices"]:
            device["media_type"] = "hdd"
        out = evaluate_raid0_policy(**data)
        self.check_contract(out, data["devices"])
        self.assertEqual([r["action"] for r in out], ["none"])

    def test_full_ssd_gives_safe_none(self):
        data = load_case("d2-temp-valid")
        for device in data["devices"]:
            if device["media_type"] == "ssd":
                device["free_bytes"] = 0
        out = evaluate_raid0_policy(**data)
        self.check_contract(out, data["devices"])
        self.assertEqual([r["action"] for r in out], ["none"])

    def test_unknown_ssd_free_space_gives_safe_none(self):
        data = load_case("d2-temp-valid")
        for device in data["devices"]:
            if device["media_type"] == "ssd":
                device["free_bytes"] = None   # unknown, not zero
        out = evaluate_raid0_policy(**data)
        self.check_contract(out, data["devices"])
        self.assertEqual([r["action"] for r in out], ["none"])

    def test_unavailable_ssd_is_never_a_target(self):
        data = load_case("d2-temp-valid")
        for device in data["devices"]:
            if device["media_type"] == "ssd":
                device["is_available"] = False
        out = evaluate_raid0_policy(**data)
        self.check_contract(out, data["devices"])
        self.assertEqual([r["action"] for r in out], ["none"])

    def test_algorithm_does_not_change_its_input(self):
        data = load_case("d2-temp-valid")
        before = copy.deepcopy(data)
        evaluate_raid0_policy(**data)
        self.assertEqual(data, before)


if __name__ == "__main__":
    unittest.main()

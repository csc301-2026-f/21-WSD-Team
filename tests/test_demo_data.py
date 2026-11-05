# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
import unittest

from backend.core.demo_data import MOCK_PATH, load_demo_input
from backend.algorithms.algo01 import evaluate_raid0_policy
from backend.algorithms.common.validation import parse_utc


class DemoDataTests(unittest.TestCase):
    HOST_ID = "core-test-host"
    EVALUATION_TIME = "2026-10-21T12:00:00Z"

    def load_inputs(self):
        return load_demo_input(
            host_id=self.HOST_ID,
            evaluation_time_utc=self.EVALUATION_TIME,
        )

    def test_host_id_comes_from_caller(self):
        data = self.load_inputs()

        self.assertEqual(data["realtime"]["host_id"], self.HOST_ID)

        for device in data["devices"]:
            self.assertEqual(device["host_id"], self.HOST_ID)

        for activity in data["history"]["file_activity"]:
            self.assertEqual(activity["host_id"], self.HOST_ID)

    def test_time_shift_preserves_activity(self):
        data = self.load_inputs()
        activity = data["history"]["file_activity"][0]

        self.assertEqual(
            data["realtime"]["evaluation_time_utc"],
            self.EVALUATION_TIME,
        )

        start = parse_utc(activity["window_start_utc"])
        end = parse_utc(activity["window_end_utc"])

        self.assertEqual((end - start).total_seconds(), 60)
        self.assertEqual(end, parse_utc(self.EVALUATION_TIME))
        self.assertEqual(activity["read_ops"], 120)
        self.assertEqual(activity["write_ops"], 0)

    def test_algorithm_returns_mock_advice_without_execution(self):
        data = self.load_inputs()

        for key in (
            "file_move",
            "file_level_pooling",
            "ssd_caching",
            "dry_run_action",
        ):
            self.assertIs(data["capabilities"][key], False)

        recommendations = evaluate_raid0_policy(**data)

        self.assertEqual(len(recommendations), 1)
        item = recommendations[0]

        self.assertEqual(item["action"], "move")
        self.assertEqual(item["file_id"], "sample-video")
        self.assertTrue(item["reason"].startswith("MOCK:"))
        self.assertIn(
            "mock_data_not_real_file_activity",
            item["constraints"],
        )
        self.assertIn(
            "file_move_execution_not_confirmed",
            item["constraints"],
        )

    def test_loads_are_independent_and_fixture_is_unchanged(self):
        original_file = MOCK_PATH.read_bytes()

        first = self.load_inputs()
        first["history"]["file_activity"][0]["read_ops"] = 0

        second = self.load_inputs()

        self.assertEqual(
            second["history"]["file_activity"][0]["read_ops"],
            120,
        )
        self.assertEqual(MOCK_PATH.read_bytes(), original_file)

    def test_invalid_inputs_are_rejected(self):
        for host_id in (None, "", "   "):
            with self.subTest(host_id=host_id):
                with self.assertRaises(ValueError):
                    load_demo_input(host_id=host_id)

        with self.assertRaises(ValueError):
            load_demo_input(
                host_id=self.HOST_ID,
                evaluation_time_utc="not-a-time",
            )


if __name__ == "__main__":
    unittest.main()
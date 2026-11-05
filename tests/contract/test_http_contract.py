"""QA contract tests for the dashboard HTTP API (T-HTTP-01)."""

import unittest

from backend.core.http_api import create_http_api

HISTORY = "/api/v1/processes/history"
GOOD = {
    "process_instance_id": "4242_2026-10-12T20:55:00Z",
    "start_utc": "2026-10-12T00:00:00Z",
    "end_utc": "2026-10-13T00:00:00Z",
}
SAMPLE_ROW = {
    "process_instance_id": "4242_2026-10-12T20:55:00Z",
    "pid": 4242,
    "process_name": "game.exe",
    "timestamp_utc": "2026-10-12T21:00:00Z",
    "read_bytes_per_sec": 31457280.0,
    "write_bytes_per_sec": 0.0,
}


class FakeCore:
    """Stands in for CoreService and records what the API asked it for."""

    def __init__(self, history=None, fail=False):
        self.history = history if history is not None else [SAMPLE_ROW]
        self.fail = fail
        self.history_calls = []

    def get_historical_process_activity(self, ids, start_utc, end_utc, bucket_seconds=None):
        if self.fail:
            raise RuntimeError("simulated CORE failure")
        self.history_calls.append((ids, start_utc, end_utc, bucket_seconds))
        return self.history

    def get_devices(self):
        return []


class HttpContractTests(unittest.TestCase):

    def client(self, core=None):
        self.core = core or FakeCore()
        app = create_http_api(self.core)
        app.testing = False  # keep the app's own error handlers active
        return app.test_client()

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status)
        body = response.get_json()
        self.assertEqual(body["status"], "error")
        self.assertIsNone(body["data"])
        self.assertEqual(body["error"]["code"], code)
        self.assertIsInstance(body["error"]["message"], str)

    # ---- success path ----------------------------------------------------

    def test_valid_request_returns_success_envelope(self):
        response = self.client().get(HISTORY, query_string=GOOD)
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body, {"status": "success", "data": [SAMPLE_ROW], "error": None})

    def test_request_is_passed_to_core_unchanged(self):
        self.client().get(HISTORY, query_string={**GOOD, "bucket_seconds": "60"})
        self.assertEqual(self.core.history_calls, [(
            [GOOD["process_instance_id"]], GOOD["start_utc"], GOOD["end_utc"], 60)])

    def test_no_history_returns_empty_list_not_error(self):
        response = self.client(FakeCore(history=[])).get(HISTORY, query_string=GOOD)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"], [])

    def test_null_values_are_not_turned_into_zero(self):
        row = {**SAMPLE_ROW, "read_bytes_per_sec": None}
        response = self.client(FakeCore(history=[row])).get(HISTORY, query_string=GOOD)
        self.assertIsNone(response.get_json()["data"][0]["read_bytes_per_sec"])

    # ---- invalid input -> 400, and CORE is never called -------------------

    def test_missing_parameters_return_400(self):
        for missing in GOOD:
            with self.subTest(missing=missing):
                params = {k: v for k, v in GOOD.items() if k != missing}
                self.assert_error(self.client().get(HISTORY, query_string=params), 400, "INVALID_REQUEST")
                self.assertEqual(self.core.history_calls, [])

    def test_non_utc_or_garbage_time_returns_400(self):
        for bad in ("yesterday", "2026-10-12 21:00", "2026-10-12T21:00:00+05:00"):
            with self.subTest(start_utc=bad):
                response = self.client().get(HISTORY, query_string={**GOOD, "start_utc": bad})
                self.assert_error(response, 400, "INVALID_REQUEST")

    def test_start_after_end_returns_400(self):
        params = {**GOOD, "start_utc": GOOD["end_utc"], "end_utc": GOOD["start_utc"]}
        self.assert_error(self.client().get(HISTORY, query_string=params), 400, "INVALID_REQUEST")

    def test_bad_bucket_seconds_returns_400(self):
        for bad in ("abc", "0", "-60", "1.5"):
            with self.subTest(bucket_seconds=bad):
                response = self.client().get(HISTORY, query_string={**GOOD, "bucket_seconds": bad})
                self.assert_error(response, 400, "INVALID_REQUEST")
                self.assertEqual(self.core.history_calls, [])

    # ---- errors use the shared envelope -------------------------------------

    def test_unknown_endpoint_returns_404_envelope(self):
        self.assert_error(self.client().get("/api/v1/does-not-exist"), 404, "NOT_FOUND")

    def test_core_failure_returns_500_envelope_without_details(self):
        response = self.client(FakeCore(fail=True)).get(HISTORY, query_string=GOOD)
        self.assert_error(response, 500, "CORE_ERROR")
        self.assertNotIn("simulated", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()

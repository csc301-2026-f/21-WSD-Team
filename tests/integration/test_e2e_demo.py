"""End-to-end test of the whole app in demo mode (T-E2E-01)."""

import shutil
import tempfile
import unittest

from backend.core.bootstrap import create_application

DEVICE_FIELDS = {
    "host_id": (str,), "device_id": (str,), "display_name": (str,),
    "media_type": (str, type(None)), "capacity_bytes": (int, type(None)),
    "free_bytes": (int, type(None)), "mount_points": (list,), "is_available": (bool,),
}
RECOMMENDATION_FIELDS = {
    "recommendation_id": (str,), "mode": (str,), "action": (str,),
    "file_id": (str, type(None)), "source_device_id": (str, type(None)),
    "target_device_id": (str, type(None)), "reason": (str,), "created_at_utc": (str,),
    "requires_approval": (bool,), "estimated_benefit": (dict, type(None)), "constraints": (list,),
}
HISTORY = ("/api/v1/processes/history?process_instance_id=4242_2026-10-12T20:55:00Z"
           "&start_utc=2026-10-12T00:00:00Z&end_utc=2026-10-13T00:00:00Z")


class EndToEndDemoTests(unittest.TestCase):

    def setUp(self):
        self.data_dir = tempfile.mkdtemp()
        self.client = self.start_app()

    def tearDown(self):
        shutil.rmtree(self.data_dir, ignore_errors=True)

    def start_app(self):
        app, _core = create_application(demo_mode=True, data_dir=self.data_dir)
        return app.test_client()

    def get_data(self, url, method="get"):
        response = getattr(self.client, method)(url)
        self.assertEqual(response.status_code, 200, url)
        body = response.get_json()
        self.assertEqual(body["status"], "success", url)
        self.assertIsNone(body["error"], url)
        return body["data"]

    def check_fields(self, record, fields):
        self.assertEqual(set(record), set(fields))
        for name, allowed in fields.items():
            self.assertIsInstance(record[name], allowed, name)

    # ---- the app starts and serves the dashboard --------------------------

    def test_dashboard_page_is_served(self):
        response = self.client.get("/", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<html", response.data.lower())

    def test_every_dashboard_endpoint_answers_in_agreed_format(self):
        for url in ("/api/v1/devices", "/api/v1/capabilities", "/api/v1/metrics/latest",
                    "/api/v1/processes/latest", "/api/v1/recommendations", HISTORY):
            with self.subTest(url=url):
                self.get_data(url)

    # ---- devices and capabilities ------------------------------------------

    def test_devices_follow_contract(self):
        devices = self.get_data("/api/v1/devices")
        self.assertGreater(len(devices), 0)
        for device in devices:
            self.check_fields(device, DEVICE_FIELDS)
            self.assertIn(device["media_type"], {"hdd", "ssd", "unknown", None})
        self.assertEqual(len({d["host_id"] for d in devices}), 1, "one machine = one host_id")

    def test_capabilities_are_true_or_false(self):
        capabilities = self.get_data("/api/v1/capabilities")
        for name, value in capabilities.items():
            if name != "notes":
                self.assertIsInstance(value, bool, name)

    # ---- recommendations: algorithm -> database -> API ---------------------

    def test_no_recommendations_before_first_refresh(self):
        self.assertEqual(self.get_data("/api/v1/recommendations"), [])

    def test_refresh_returns_contract_valid_recommendations(self):
        recommendations = self.get_data("/api/v1/recommendations/refresh", method="post")
        self.assertGreater(len(recommendations), 0)
        for rec in recommendations:
            self.check_fields(rec, RECOMMENDATION_FIELDS)
            self.assertEqual(rec["mode"], "raid0")
            self.assertIsNone(rec["estimated_benefit"], "no unmeasured speed-up claims")
            self.assertTrue(rec["created_at_utc"].endswith("Z"))
            if rec["action"] == "move":
                self.assertIs(rec["requires_approval"], True)

    def test_recommendations_point_at_real_devices(self):
        devices = {d["device_id"]: d for d in self.get_data("/api/v1/devices")}
        for rec in self.get_data("/api/v1/recommendations/refresh", method="post"):
            if rec["action"] == "move":
                self.assertEqual(devices[rec["source_device_id"]]["media_type"], "hdd")
                self.assertEqual(devices[rec["target_device_id"]]["media_type"], "ssd")

    def test_saved_recommendations_come_back_unchanged(self):
        refreshed = self.get_data("/api/v1/recommendations/refresh", method="post")
        self.assertEqual(self.get_data("/api/v1/recommendations"), refreshed)

    def test_recommendations_survive_restart(self):
        refreshed = self.get_data("/api/v1/recommendations/refresh", method="post")
        self.client = self.start_app()
        self.assertEqual(self.get_data("/api/v1/recommendations"), refreshed)

    def test_mode_filter(self):
        refreshed = self.get_data("/api/v1/recommendations/refresh", method="post")
        self.assertEqual(self.get_data("/api/v1/recommendations?mode=raid0"), refreshed)
        self.assertEqual(self.get_data("/api/v1/recommendations?mode=ssd_caching"), [])

    @unittest.expectedFailure  # Known bug (see GitHub Issue): remove this line once fixed
    def test_refreshing_twice_does_not_duplicate_recommendations(self):
        self.get_data("/api/v1/recommendations/refresh", method="post")
        latest = self.get_data("/api/v1/recommendations/refresh", method="post")
        self.assertEqual(len(self.get_data("/api/v1/recommendations")), len(latest))

    # ---- US-02 history endpoint is wired through to the database -----------

    def test_history_endpoint_reaches_database(self):
        self.assertEqual(self.get_data(HISTORY), [])

    def test_history_endpoint_rejects_bad_input(self):
        response = self.client.get("/api/v1/processes/history?process_instance_id=x")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "INVALID_REQUEST")


if __name__ == "__main__":
    unittest.main()

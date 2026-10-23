# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""John's schema compatibility examples; no OS, DB, HTTP or GUI integration."""
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from backend.algorithms.algo01.demo import main
FIXTURES = Path(__file__).parent / 'fixtures'
FIELDS = {'host_id', 'pid', 'start_time_utc', 'process_name', 'timestamp_utc', 'sample_window_seconds', 'read_bytes_per_sec', 'write_bytes_per_sec', 'attributed_device_id'}

def load(name):
    return json.loads((FIXTURES / name).read_text(encoding='utf-8'))

def instance_id(row):
    """Test-only encoding proposal: unknown start time cannot produce a stable ID."""
    if row['start_time_utc'] is None:
        return None
    return 'process:' + json.dumps([row['host_id'], row['pid'], row['start_time_utc']], separators=(',', ':'))

class ProcessFixtureTests(unittest.TestCase):

    def check_row(self, row):
        self.assertEqual(set(row), FIELDS)
        self.assertIsInstance(row['host_id'], str)
        self.assertIs(type(row['pid']), int)
        self.assertGreater(row['pid'], 0)
        for key in ('start_time_utc', 'timestamp_utc'):
            if row[key] is not None:
                self.assertEqual(datetime.fromisoformat(row[key].replace('Z', '+00:00')).utcoffset().total_seconds(), 0)
        self.assertGreater(row['sample_window_seconds'], 0)
        for key in ('read_bytes_per_sec', 'write_bytes_per_sec'):
            self.assertTrue(row[key] is None or (type(row[key]) in (int, float) and row[key] >= 0))
        for key in ('process_name', 'attributed_device_id'):
            self.assertTrue(row[key] is None or isinstance(row[key], str))

    def test_juan_latest_shape_and_null_not_zero(self):
        rows = load('upstream_juan/metrics_process.json')
        for row in rows:
            self.check_row(row)
        self.assertEqual(rows[0]['write_bytes_per_sec'], 0.0)
        self.assertIsNone(rows[1]['write_bytes_per_sec'])
        self.assertIsNone(instance_id(rows[1]))

    def test_mock_history_series_query_and_empty(self):
        rows = load('process-history-mock.json')
        query = load('process-history-query-proposed.json')['query']
        start = datetime.fromisoformat(query['start_utc'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(query['end_utc'].replace('Z', '+00:00'))
        for row in rows:
            self.check_row(row)
            self.assertIn(instance_id(row), query['process_instance_ids'])
            observed = datetime.fromisoformat(row['timestamp_utc'].replace('Z', '+00:00'))
            self.assertTrue(start <= observed < end)
        self.assertEqual([x['timestamp_utc'] for x in rows], sorted((x['timestamp_utc'] for x in rows)))
        self.assertEqual(load('process-history-empty.json'), [])
        self.assertEqual(load('upstream_juan/history_empty.json'), [])

    def test_reused_pid_is_a_different_instance(self):
        row = load('upstream_juan/metrics_process.json')[0]
        restarted = {**row, 'start_time_utc': '2026-10-12T22:00:00Z'}
        self.assertNotEqual(instance_id(row), instance_id(restarted))

    def test_juan_recommendations_share_record_fields_but_pending_list_semantics(self):
        rows = load('upstream_juan/recommendations_raid0.json')
        self.assertEqual([x['action'] for x in rows], ['move', 'none'])
        self.assertTrue(rows[1]['requires_approval'])
        for row in rows:
            self.assertEqual(row['mode'], 'raid0')
            self.assertIsNone(row['estimated_benefit'])
if __name__ == '__main__':
    unittest.main()

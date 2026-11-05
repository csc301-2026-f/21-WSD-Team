# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
import unittest
import time

from backend.core.collector_agent import CollectorAgent


class FakeCore:
    def __init__(self):
        self.count = 0

    def collect_and_record(self):
        self.count += 1

class TestCollectorAgent(unittest.TestCase):

    def test_start_and_stop(self): # base test
        core = FakeCore()
        collector = CollectorAgent(core, interval_seconds=0.05)

        collector.start()
        time.sleep(0.25)
        collector.stop()

        self.assertGreater(core.count, 0)
        self.assertIsNone(collector.thread)

    def test_start_twice(self): # test twice activate collection, rst logical
        core = FakeCore()
        collector = CollectorAgent(core, interval_seconds=0.05)

        collector.start()
        first_thread = collector.thread

        collector.start()

        self.assertIs(collector.thread, first_thread)

        collector.stop()
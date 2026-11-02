# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""An agent periodically trigger CORE data collection"""

import threading
import logging

class CollectorAgent:
    def __init__(self, core, interval_seconds=1):
        if interval_seconds <= 0:
            raise ValueError("Collection interval can't be non-positive number")

        self.core = core
        self.interval_seconds = interval_seconds
        self.stop_event = threading.Event() # stop event for end collecting
        self.thread = None # the thread use to collect
        self.last_error = None # msg for why error

    def _collect_loop(self):
        while not self.stop_event.wait(self.interval_seconds): # no stop signal?
            try: # skip failure collection
                self.core.collect_and_record()
                self.last_error = None
            except Exception as error:
                self.last_error = str(error)
                logging.exception("Collection failed")

    def start(self):
        # Guarantee only one collection thread
        if self.thread is not None and self.thread.is_alive():
            return

        # Rst stop sgl in the past
        self.stop_event.clear()

        # Create a new collection thread
        self.thread = threading.Thread(target=self._collect_loop,name="wsd-collectagent")

        self.thread.start()

    def stop(self):
        # Sgl collection agent thread stop
        self.stop_event.set()

        # wait thread finish
        if self.thread is not None:
            self.thread.join()
            self.thread = None
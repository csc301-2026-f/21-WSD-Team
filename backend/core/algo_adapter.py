# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
## Might change after Algorithm merged
class AlgorithmAdapter:
    def __init__(self, evaluator):
        self.evaluator = evaluator

    def evaluate_raid0(self, devices: list[dict], realtime: dict, history: dict,
                       mode_config: dict, capabilities: dict):
        return self.evaluator(devices, realtime, history, mode_config, capabilities)
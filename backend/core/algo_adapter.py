# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
class AlgorithmAdapter:
    def __init__(self, raid0_evaluator, ssd_evaluator):
        self.raid0_evaluator = raid0_evaluator
        self.ssd_evaluator = ssd_evaluator

    def evaluate_raid0(self, devices: list[dict], realtime: dict, history: dict,
                       mode_config: dict, capabilities: dict) -> list[dict]:
        return self.raid0_evaluator(devices, realtime, history, mode_config, capabilities)

    def evaluate_ssd(self, devices: list[dict], realtime: dict, history: dict,
                     mode_config: dict, capabilities: dict) -> list[dict]:
        return self.ssd_evaluator(devices, realtime, history, mode_config, capabilities)

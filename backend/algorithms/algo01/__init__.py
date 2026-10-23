# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""John's D2 file-advice entry. Advanced interfaces live in the private prototype."""
from .raid0_policy import evaluate_raid0_policy
from .inputs import PolicyInputError
__all__ = ["evaluate_raid0_policy", "PolicyInputError"]

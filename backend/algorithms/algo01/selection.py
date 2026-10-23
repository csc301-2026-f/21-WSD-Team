# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Compatibility import for the working D2 selection function."""
from .greedy_selection import select_recommendations
__all__ = ["select_recommendations"]

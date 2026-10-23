"""Jesslyn's D2 SSD caching advice entry point."""
from .ssd_policy import evaluate_ssd_caching_policy
from .inputs import PolicyInputError

__all__ = ["evaluate_ssd_caching_policy", "PolicyInputError"]
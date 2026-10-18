"""Working D2 helpers; no advanced placeholder exports."""
from .validation import is_number, is_integer, is_text, parse_utc, is_fresh, is_mock_source
from .capacity import index_devices, build_ssd_budgets
from .recommendations import make_recommendation, make_none
__all__ = ["is_number", "is_integer", "is_text", "parse_utc", "is_fresh", "is_mock_source",
           "index_devices", "build_ssd_budgets", "make_recommendation", "make_none"]

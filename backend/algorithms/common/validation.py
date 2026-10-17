"""Small value/time validators usable by either policy without OS dependencies."""

import math
from datetime import datetime, timezone


def is_number(value, minimum=0):
    """A finite int/float, excluding bool; huge integers fail closed."""
    try:
        return (type(value) in (int, float) and math.isfinite(value)
                and value >= minimum)
    except OverflowError:
        return False


def is_integer(value, minimum=0):
    return type(value) is int and minimum <= value <= 2**63 - 1


def is_text(value):
    return isinstance(value, str) and bool(value.strip())


def parse_utc(value):
    """Parse an explicitly UTC timestamp; never consult the system clock."""
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("timestamp must include UTC offset")
    return parsed.astimezone(timezone.utc)


def is_fresh(value, now, max_age):
    try:
        return 0 <= (now - parse_utc(value)).total_seconds() <= max_age
    except (ValueError, TypeError, OverflowError):
        return False


def is_mock_source(value):
    """Recognize mock or mock:<description> in the existing source field."""
    return isinstance(value, str) and value.strip().casefold().split(":", 1)[0] == "mock"

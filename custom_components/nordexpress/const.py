"""Constants for Nord Express."""

DOMAIN = "nordexpress"
BASE_URL = "https://nordexpress.kiedyprzyjedzie.pl"
TIME_ZONE = "Europe/Warsaw"
POLL_SECONDS = 30
HORIZON_DAYS = 7
MAX_CALENDAR_DAYS = 14


def validate_calendar_days(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Expected whole days")
    if not 1 <= value <= MAX_CALENDAR_DAYS or int(value) != value:
        raise ValueError("Expected 1 to 14 days")
    return int(value)

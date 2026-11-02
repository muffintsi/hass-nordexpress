"""Transport data normalization, independent of Home Assistant.

Service times are wall-clock seconds since the service date, not UTC elapsed
seconds. Real-time display strings have minute precision; never imply GPS
second-level precision from them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

WARSAW = ZoneInfo("Europe/Warsaw")


def normalize_directions(value) -> tuple[str, ...]:
    """Keep deterministic, nonempty selections; accept legacy single destinations."""
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError("Select at least one destination")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError("Invalid destination")
    return tuple(sorted(set(value)))


def configured_directions(config, options=None) -> tuple[str, ...]:
    options = options or {}
    return normalize_directions(
        options.get("directions", config.get("directions", config.get("direction")))
    )


def configured_routes(config, options=None) -> dict[str, tuple[str, ...]]:
    """Read stop-wide selections and legacy single-line entries."""
    options = options or {}
    routes = options.get("routes", config.get("routes"))
    if routes is None:
        return {str(config["line"]): configured_directions(config, options)}
    if not isinstance(routes, dict) or not routes:
        raise ValueError("Select at least one line")
    return {str(line): normalize_directions(directions) for line, directions in routes.items()}


def route_identity(config, unique_id, line):
    """Keep the original identity for the line in a legacy configuration."""
    return unique_id if str(config.get("line", "")) == line else f"{unique_id}_{line}"


def instant(value: datetime) -> datetime:
    """Use UTC for ordering (including repeated hours during DST)."""
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class Departure:
    scheduled: datetime
    direction: str
    line: str
    trip_id: int
    stop_index: int
    platform: str | None = None
    symbols: str = ""
    expected: datetime | None = None
    estimated: bool = False
    canceled: bool = False
    at_stop: bool = False
    display_time: str | None = None

    @property
    def when(self) -> datetime:
        return self.expected or self.scheduled

    def as_dict(self) -> dict:
        return {
            "scheduled": self.scheduled.isoformat(),
            "expected": self.expected.isoformat() if self.expected else None,
            "direction": self.direction,
            "line": self.line,
            "trip_id": self.trip_id,
            "stop_index": self.stop_index,
            "platform": self.platform,
            "symbols": self.symbols,
            "estimated": self.estimated,
            "canceled": self.canceled,
            "at_stop": self.at_stop,
            "display_time": self.display_time,
            "precision": "minute",
        }


def timetable(payload: dict, service_date: date, line: str) -> list[Departure]:
    """Decode variant symbols exactly as the passenger frontend does."""
    main = (payload.get("main_direction") or {}).get("name", "")
    variants = {
        item["symbol"]: item["name"] for item in payload.get("directions", []) if item.get("symbol")
    }
    result = []
    for row in payload["departures"]:
        seconds = int(row["departure"])
        if seconds < 0 or seconds > 172800:
            raise ValueError("Invalid departure seconds")
        symbols = row.get("symbols", "")
        direction = main
        for symbol in symbols:
            if symbol in variants:
                direction = variants[symbol]
        wall = datetime.combine(service_date, time()) + timedelta(seconds=seconds)
        scheduled = wall.replace(tzinfo=WARSAW)
        # Skip nonexistent spring-transition times instead of silently shifting.
        if instant(scheduled).astimezone(WARSAW).replace(tzinfo=None) != wall:
            continue
        result.append(
            Departure(
                scheduled=scheduled,
                direction=direction,
                line=line,
                trip_id=int(row["trip_id"]),
                stop_index=int(row["index"]),
                platform=row.get("platform", payload.get("platform")),
                symbols=symbols,
            )
        )
    return sorted(result, key=lambda item: instant(item.when))


def display_instant(text: str, reference: datetime) -> datetime | None:
    """Decode observed frontend formats using the API timestamp, never fetch time."""
    if re.fullmatch(r"<\s*1\s*min", text):
        return reference  # Imminent; the API does not expose an exact second.
    if match := re.fullmatch(r"(\d+)\s*min", text):
        return (instant(reference) + timedelta(minutes=int(match[1]))).astimezone(WARSAW)
    if match := re.fullmatch(r"([0-2]?\d):([0-5]\d)", text):
        hour, minute = map(int, match.groups())
        if hour > 23:
            return None
        candidates = []
        for day in (-1, 0, 1):
            wall = datetime.combine(reference.date() + timedelta(days=day), time(hour, minute))
            for fold in (0, 1):
                candidate = wall.replace(tzinfo=WARSAW, fold=fold)
                if instant(candidate).astimezone(WARSAW).replace(tzinfo=None) == wall:
                    candidates.append(candidate)
        if candidates:
            return min(
                candidates,
                key=lambda item: abs((instant(item) - instant(reference)).total_seconds()),
            )
    return None


def merge_live(departures: list[Departure], payload: dict, now: datetime) -> list[Departure]:
    """Match by trip AND stop index; the same trip id repeats on different days."""
    reference = datetime.fromtimestamp(payload["timestamp"], timezone.utc).astimezone(WARSAW)
    if not -30 <= (instant(now) - instant(reference)).total_seconds() <= 120:
        raise ValueError("Stale real-time response")
    result = list(departures)
    for row in payload["rows"]:
        predicted = display_instant(row.get("time", ""), reference)
        anchor = predicted or reference
        candidates = [
            (index, item)
            for index, item in enumerate(result)
            if item.trip_id == int(row["trip_id"])
            and item.stop_index == int(row["trip_index"])
            and item.line == str(row["line_name"])
            and abs((instant(item.scheduled) - instant(anchor)).total_seconds()) < 43200
        ]
        if not candidates:
            continue
        index, item = min(
            candidates,
            key=lambda pair: abs((instant(pair[1].scheduled) - instant(anchor)).total_seconds()),
        )
        direction = payload.get("directions", {}).get(str(row.get("direction_id")), item.direction)
        result[index] = replace(
            item,
            expected=predicted if row.get("is_estimated") else None,
            estimated=bool(row.get("is_estimated") and predicted is not None),
            canceled=bool(row.get("canceled")),
            at_stop=bool(row.get("at_stop")),
            direction=direction,
            platform=row.get("platform") or item.platform,
            display_time=row.get("time"),
        )
    return sorted(result, key=lambda item: instant(item.when))


def upcoming(
    departures: list[Departure], direction: str | list | tuple, now: datetime
) -> list[Departure]:
    """Retain imminent live rows until the next poll; exclude canceled trips."""
    selected = normalize_directions(direction)
    return sorted(
        [
            item
            for item in departures
            if item.direction in selected
            and not item.canceled
            and (
                instant(item.when) >= instant(now)
                or (
                    item.estimated
                    and 0 <= (instant(now) - instant(item.when)).total_seconds() <= 60
                )
            )
        ],
        key=lambda item: instant(item.when),
    )

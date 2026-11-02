"""Presentation contract shared with hass-zim-slupsk dashboards."""

from datetime import timedelta

from .model import instant


def zim_attributes(departures, config):
    first = departures[0] if departures else None
    second = departures[1] if len(departures) > 1 else None
    return {
        "line": config["line"],
        "Direction": first.direction if first else None,
        "BusHour": first.when.strftime("%H:%M") if first else None,
        "NextBusDirection": second.direction if second else None,
        "NextBusTime": second.when.strftime("%Y-%m-%d %H:%M") if second else None,
        "NextBusHour": second.when.strftime("%H:%M") if second else None,
        "latitude": config.get("latitude"),
        "longitude": config.get("longitude"),
        "stop_name": config["stop_name"],
        "stop_code": config.get("stop_code"),
    }


def calendar_records(departures, direction, start, end):
    """ZIM-compatible one-minute planned departures and half-open query ranges."""
    result = []
    for item in departures:
        event_start = instant(item.scheduled)
        event_end = event_start + timedelta(minutes=1)
        if item.direction != direction or item.canceled:
            continue
        if event_end <= instant(start) or event_start >= instant(end):
            continue
        title = f"Linia {item.line} → {item.direction}"
        result.append(
            {
                "summary": title,
                "description": title,
                "start": item.scheduled,
                "end": event_end.astimezone(item.scheduled.tzinfo),
            }
        )
    return sorted(result, key=lambda record: instant(record["start"]))

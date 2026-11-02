"""Shared fetching and date-aware timetable coordination."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NordExpressApi, NordExpressError
from .const import HORIZON_DAYS, POLL_SECONDS, validate_calendar_days
from .model import WARSAW, configured_routes, instant, merge_live, timetable, upcoming

LOGGER = logging.getLogger(__name__)


class NordExpressCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, api: NordExpressApi, entry, line=None) -> None:
        super().__init__(
            hass,
            LOGGER,
            name=entry.title,
            update_interval=timedelta(seconds=POLL_SECONDS),
            config_entry=entry,
        )
        self.api = api
        routes = configured_routes(entry.data, entry.options)
        if line is None:
            if len(routes) != 1:
                raise ValueError("Specify a line for a multi-line entry")
            line = next(iter(routes))
        selected = routes[line]
        self.config = {
            **entry.data,
            "line": line,
            "directions": list(selected),
            "direction": " / ".join(selected),
        }
        self.calendar_days = validate_calendar_days(
            entry.options.get("calendar_days", HORIZON_DAYS)
        )

    async def _async_update_data(self) -> dict:
        now = datetime.now(WARSAW)
        stop, line = self.config["stop_id"], self.config["line"]
        try:
            departures = []
            # Yesterday includes service times beyond 24:00 and delayed late trips.
            for offset in range(-1, self.calendar_days):
                day = now.date() + timedelta(days=offset)
                departures.extend(timetable(await self.api.timetable(stop, line, day), day, line))
        except (NordExpressError, KeyError, TypeError, ValueError) as error:
            raise UpdateFailed(f"Timetable unavailable: {error}") from error

        live_available = False
        live_timestamp = None
        try:
            live = await self.api.departures(stop)
            departures = merge_live(departures, live, now)
            live_available = True
            live_timestamp = live["timestamp"]
        except (NordExpressError, KeyError, TypeError, ValueError, OverflowError) as error:
            LOGGER.debug("Using timetable without real-time data: %s", error)

        direction = self.config["directions"]
        return {
            "departures": departures,
            "realtime_available": live_available,
            "realtime_timestamp": live_timestamp,
            "schedule_updated": now.isoformat(),
            "horizon_end": (now.date() + timedelta(days=self.calendar_days - 1)).isoformat(),
            "canceled": [
                item.as_dict()
                for item in departures
                if item.canceled
                and item.direction in direction
                and instant(item.when) >= instant(now)
            ],
            "upcoming": upcoming(departures, direction, now),
        }

"""Departure calendars following the hass-zim-slupsk presentation convention."""

from datetime import datetime, time, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .model import WARSAW, instant, route_identity
from .presentation import calendar_records


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [NordExpressCalendar(entry, coordinator) for coordinator in entry.runtime_data.values()]
    )


class NordExpressCalendar(CoordinatorEntity, CalendarEntity):
    _attr_icon = "mdi:calendar"

    def __init__(self, entry, coordinator):
        super().__init__(coordinator)
        line = coordinator.config["line"]
        self._attr_unique_id = f"{route_identity(entry.data, entry.unique_id, line)}_calendar"
        self._attr_name = f"Linia {line} - {entry.data['stop_name']}"
        # Share the sensor's device so the calendar is visible beside it in HA.
        self._attr_device_info = {
            "identifiers": {(DOMAIN, route_identity(entry.data, entry.unique_id, line))},
        }
        self._attr_extra_state_attributes = {
            "calendar_days": self.coordinator.calendar_days,
            "line": line,
            "latitude": entry.data.get("latitude"),
            "longitude": entry.data.get("longitude"),
            "stop_name": entry.data["stop_name"],
            "stop_code": entry.data.get("stop_code"),
        }

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(self.hass, self._tick, timedelta(seconds=30))
        )

    @callback
    def _tick(self, _now):
        self.async_write_ha_state()

    def _records(self, start, end):
        data = self.coordinator.data or {}
        today = datetime.now(WARSAW).date()
        window_start = datetime.combine(today, time(), WARSAW)
        window_end = window_start + timedelta(days=self.coordinator.calendar_days)
        start = max(instant(start), instant(window_start))
        end = min(instant(end), instant(window_end))
        if start >= end:
            return []
        return calendar_records(
            data.get("departures", []), self.coordinator.config["directions"], start, end
        )

    @property
    def event(self):
        now = datetime.now(WARSAW)
        events = self._records(now, now + timedelta(days=self.coordinator.calendar_days))
        return CalendarEvent(**events[0]) if events else None

    async def async_get_events(self, hass, start_date, end_date):
        return [CalendarEvent(**record) for record in self._records(start_date, end_date)]

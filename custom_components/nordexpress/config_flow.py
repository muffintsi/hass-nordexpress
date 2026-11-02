"""UI configuration: stop, line, and exact destination."""

from datetime import datetime, timedelta
from uuid import uuid4

try:
    import probatio as vol
except ImportError:
    import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from . import get_api
from .api import NordExpressError
from .const import DOMAIN, HORIZON_DAYS, MAX_CALENDAR_DAYS, validate_calendar_days
from .model import WARSAW, configured_directions, normalize_directions, timetable


def selection(options, multiple=False):
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options,
            multiple=multiple,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


async def destinations(hass, stop, line):
    result = set()
    today = datetime.now(WARSAW).date()
    for offset in range(HORIZON_DAYS):
        day = today + timedelta(days=offset)
        payload = await get_api(hass).timetable(stop, line, day)
        result.update(item.direction for item in timetable(payload, day, line) if item.direction)
    return sorted(result)


def duplicate(hass, stop, line, selected, exclude=None):
    return any(
        entry.entry_id != exclude
        and entry.data.get("stop_id") == stop
        and entry.data.get("line") == line
        and configured_directions(entry.data, entry.options) == selected
        for entry in hass.config_entries.async_entries(DOMAIN)
    )


class NordExpressConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return NordExpressOptionsFlow()

    def __init__(self):
        self._stops = []
        self._stop = None
        self._lines = []
        self._line = None
        self._destinations = []

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            self._stop = next(
                (stop for stop in self._stops if stop["id"] == user_input["stop_id"]), None
            )
            if self._stop is not None:
                return await self.async_step_line()
            errors["base"] = "invalid_selection"
        try:
            self._stops = await get_api(self.hass).stops()
        except NordExpressError:
            errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required("stop_id"): selection(
                        [
                            {"value": stop["id"], "label": f"{stop['name']} ({stop['number']})"}
                            for stop in sorted(
                                self._stops, key=lambda stop: (stop["name"], stop["id"])
                            )
                        ]
                    ),
                }
            ),
        )

    async def async_step_line(self, user_input=None):
        errors = {}
        if user_input is not None:
            if user_input["line"] in self._lines:
                self._line = user_input["line"]
                return await self.async_step_direction()
            errors["base"] = "invalid_selection"
        try:
            lines = set()
            for offset in range(HORIZON_DAYS):
                day = datetime.now(WARSAW).date() + timedelta(days=offset)
                lines.update(
                    str(row["line"])
                    for row in await get_api(self.hass).directions(self._stop["id"], day)
                )
            self._lines = sorted(lines)
            if not self._lines:
                errors["base"] = "no_lines"
        except (NordExpressError, KeyError, TypeError, ValueError):
            errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="line",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required("line"): selection(self._lines),
                }
            ),
        )

    async def async_step_direction(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                selected = normalize_directions(user_input.get("directions", []))
                if not set(selected).issubset(self._destinations):
                    raise ValueError("Unknown destination")
            except ValueError:
                errors["base"] = "invalid_selection"
            else:
                if duplicate(self.hass, self._stop["id"], self._line, selected):
                    return self.async_abort(reason="already_configured")
                # Keep identity independent of editable destination selections.
                await self.async_set_unique_id(uuid4().hex)
                label = " / ".join(selected)
                return self.async_create_entry(
                    title=f"{self._stop['name']} · {self._line} → {label}",
                    data={
                        "stop_id": self._stop["id"],
                        "stop_name": self._stop["name"],
                        "line": self._line,
                        "directions": list(selected),
                        "direction": label,
                        "latitude": self._stop["latitude"],
                        "longitude": self._stop["longitude"],
                        "stop_code": str(self._stop["number"]),
                    },
                )
        try:
            self._destinations = await destinations(self.hass, self._stop["id"], self._line)
            if not self._destinations:
                errors["base"] = "no_departures"
        except (NordExpressError, KeyError, TypeError, ValueError):
            errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="direction",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required("directions"): selection(self._destinations, multiple=True),
                }
            ),
        )


class NordExpressOptionsFlow(config_entries.OptionsFlow):
    def __init__(self):
        self._destinations = None

    async def async_step_init(self, user_input=None):
        errors = {}
        entry = self.config_entry
        selected = configured_directions(entry.data, entry.options)
        if self._destinations is None:
            try:
                available = await destinations(self.hass, entry.data["stop_id"], entry.data["line"])
            except (NordExpressError, KeyError, TypeError, ValueError):
                available = []
                errors["base"] = "cannot_connect"
            # A destination temporarily absent from the schedule remains selectable.
            self._destinations = sorted(set(available) | set(selected))
        if user_input is not None:
            try:
                days = validate_calendar_days(user_input["calendar_days"])
            except (ValueError, KeyError):
                errors["calendar_days"] = "invalid_calendar_days"
            try:
                selected = normalize_directions(user_input.get("directions", list(selected)))
                if not set(selected).issubset(self._destinations):
                    raise ValueError("Unknown destination")
            except ValueError:
                errors["directions"] = "invalid_selection"
            else:
                if duplicate(
                    self.hass, entry.data["stop_id"], entry.data["line"], selected, entry.entry_id
                ):
                    errors["base"] = "already_configured"
            if not errors:
                return self.async_create_entry(
                    title="",
                    data={
                        **entry.options,
                        "calendar_days": days,
                        "directions": list(selected),
                    },
                )
        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required("directions", default=list(selected)): selection(
                        self._destinations, multiple=True
                    ),
                    vol.Required(
                        "calendar_days", default=entry.options.get("calendar_days", HORIZON_DAYS)
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1,
                            max=MAX_CALENDAR_DAYS,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
        )

"""Configure an independent group of lines and destinations at one stop."""

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
from .model import WARSAW, configured_routes, normalize_directions, timetable


def selection(options, multiple=False):
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options,
            multiple=multiple,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


async def available_lines(hass, stop):
    result = set()
    today = datetime.now(WARSAW).date()
    for offset in range(HORIZON_DAYS):
        rows = await get_api(hass).directions(stop, today + timedelta(days=offset))
        result.update(str(row["line"]) for row in rows)
    return sorted(result)


async def destinations(hass, stop, line):
    result = set()
    today = datetime.now(WARSAW).date()
    for offset in range(HORIZON_DAYS):
        day = today + timedelta(days=offset)
        payload = await get_api(hass).timetable(stop, line, day)
        result.update(item.direction for item in timetable(payload, day, line) if item.direction)
    return sorted(result)


def duplicate(hass, stop, routes, exclude=None):
    return any(
        entry.entry_id != exclude
        and entry.data.get("stop_id") == stop
        and configured_routes(entry.data, entry.options) == routes
        for entry in hass.config_entries.async_entries(DOMAIN)
    )


def title(stop_name, routes):
    return (
        stop_name
        + " · "
        + "; ".join(f"{line} → {' / '.join(directions)}" for line, directions in routes.items())
    )


class DirectionSteps:
    """Ask separately about destinations for every explicitly selected line."""

    def _start_directions(self, lines, current=None):
        self._selected_lines = list(lines)
        self._routes = {}
        self._line_index = 0
        self._known = {}
        self._previous_routes = current or {}

    async def async_step_direction(self, user_input=None):
        line = self._selected_lines[self._line_index]
        errors = {}
        if line not in self._known or not self._known[line]:
            try:
                known = await destinations(self.hass, self._stop_id, line)
            except (NordExpressError, KeyError, TypeError, ValueError):
                known = []
                errors["base"] = "cannot_connect"
            self._known[line] = sorted(set(known) | set(self._previous_routes.get(line, ())))
        if user_input is not None and not errors:
            try:
                selected = normalize_directions(user_input.get("directions", []))
                if not set(selected).issubset(self._known[line]):
                    raise ValueError("Unknown destination")
            except ValueError:
                errors["base"] = "invalid_selection"
            else:
                self._routes[line] = selected
                if self._line_index + 1 < len(self._selected_lines):
                    self._line_index += 1
                    return await self.async_step_direction()
                return await self._finish_routes()
        if not self._known[line] and not errors:
            errors["base"] = "no_departures"
        return self.async_show_form(
            step_id="direction",
            errors=errors,
            description_placeholders={"line": line},
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "directions", default=list(self._previous_routes.get(line, ()))
                    ): selection(self._known[line], multiple=True),
                }
            ),
        )


class NordExpressConfigFlow(DirectionSteps, config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return NordExpressOptionsFlow()

    def __init__(self):
        self._stops = []
        self._stop = None
        self._lines = []

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            self._stop = next(
                (stop for stop in self._stops if stop["id"] == user_input["stop_id"]), None
            )
            if self._stop is not None:
                self._stop_id = self._stop["id"]
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
            try:
                lines = normalize_directions(user_input.get("lines", []))
                if not set(lines).issubset(self._lines):
                    raise ValueError("Unknown line")
            except ValueError:
                errors["base"] = "invalid_selection"
            else:
                self._start_directions(lines)
                return await self.async_step_direction()
        try:
            self._lines = await available_lines(self.hass, self._stop_id)
            if not self._lines:
                errors["base"] = "no_lines"
        except (NordExpressError, KeyError, TypeError, ValueError):
            errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="line",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required("lines"): selection(self._lines, multiple=True),
                }
            ),
        )

    async def _finish_routes(self):
        if duplicate(self.hass, self._stop_id, self._routes):
            return self.async_abort(reason="already_configured")
        await self.async_set_unique_id(uuid4().hex)
        return self.async_create_entry(
            title=title(self._stop["name"], self._routes),
            data={
                "stop_id": self._stop_id,
                "stop_name": self._stop["name"],
                "latitude": self._stop["latitude"],
                "longitude": self._stop["longitude"],
                "stop_code": str(self._stop["number"]),
                "routes": {line: list(directions) for line, directions in self._routes.items()},
            },
        )


class NordExpressOptionsFlow(DirectionSteps, config_entries.OptionsFlow):
    def __init__(self):
        self._lines = None

    async def async_step_init(self, user_input=None):
        errors = {}
        entry = self.config_entry
        self._stop_id = entry.data["stop_id"]
        current = configured_routes(entry.data, entry.options)
        if self._lines is None:
            try:
                available = await available_lines(self.hass, self._stop_id)
            except (NordExpressError, KeyError, TypeError, ValueError):
                available = []
                errors["base"] = "cannot_connect"
            self._lines = sorted(set(available) | set(current))
        if user_input is not None:
            try:
                self._days = validate_calendar_days(user_input["calendar_days"])
            except (KeyError, ValueError):
                errors["calendar_days"] = "invalid_calendar_days"
            try:
                lines = normalize_directions(user_input.get("lines", list(current)))
                if not set(lines).issubset(self._lines):
                    raise ValueError("Unknown line")
            except ValueError:
                errors["lines"] = "invalid_selection"
            if not errors:
                self._start_directions(lines, current)
                return await self.async_step_direction()
        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required("lines", default=list(current)): selection(
                        self._lines, multiple=True
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

    async def _finish_routes(self):
        entry = self.config_entry
        if duplicate(self.hass, self._stop_id, self._routes, entry.entry_id):
            return self.async_abort(reason="already_configured")
        return self.async_create_entry(
            title="",
            data={
                **{key: value for key, value in entry.options.items() if key != "directions"},
                "calendar_days": self._days,
                "routes": {line: list(directions) for line, directions in self._routes.items()},
            },
        )

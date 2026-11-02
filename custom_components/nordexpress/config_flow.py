"""UI configuration: stop, line, and exact destination."""

from datetime import datetime, timedelta

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
from .model import WARSAW, timetable


def selection(options):
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
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
            direction = user_input["direction"]
            if direction in self._destinations:
                await self.async_set_unique_id(f"{self._stop['id']}|{self._line}|{direction}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"{self._stop['name']} · {self._line} → {direction}",
                    data={
                        "stop_id": self._stop["id"],
                        "stop_name": self._stop["name"],
                        "line": self._line,
                        "direction": direction,
                        "latitude": self._stop["latitude"],
                        "longitude": self._stop["longitude"],
                        "stop_code": str(self._stop["number"]),
                    },
                )
            errors["base"] = "invalid_selection"
        try:
            destinations = set()
            for offset in range(HORIZON_DAYS):
                day = datetime.now(WARSAW).date() + timedelta(days=offset)
                payload = await get_api(self.hass).timetable(self._stop["id"], self._line, day)
                destinations.update(
                    item.direction for item in timetable(payload, day, self._line) if item.direction
                )
            self._destinations = sorted(destinations)
            if not self._destinations:
                errors["base"] = "no_departures"
        except (NordExpressError, KeyError, TypeError, ValueError):
            errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="direction",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required("direction"): selection(self._destinations),
                }
            ),
        )


class NordExpressOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                days = validate_calendar_days(user_input["calendar_days"])
            except (ValueError, KeyError):
                errors["calendar_days"] = "invalid_calendar_days"
            else:
                return self.async_create_entry(
                    title="",
                    data={
                        **self.config_entry.options,
                        "calendar_days": days,
                    },
                )
        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "calendar_days",
                        default=self.config_entry.options.get("calendar_days", HORIZON_DAYS),
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

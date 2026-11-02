"""Exercise real HA classes without the Unix-only pytest harness or a server."""

import asyncio
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from types import MappingProxyType
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from homeassistant.config_entries import ConfigEntries, ConfigEntry  # noqa: E402
from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.helpers import device_registry as dr  # noqa: E402
from homeassistant.helpers import entity_registry as er

from custom_components.nordexpress import async_remove_obsolete_sensors  # noqa: E402
from custom_components.nordexpress.calendar import async_setup_entry as setup_calendars  # noqa: E402
from custom_components.nordexpress.config_flow import NordExpressConfigFlow, NordExpressOptionsFlow  # noqa: E402
from custom_components.nordexpress.coordinator import NordExpressCoordinator  # noqa: E402
from custom_components.nordexpress.model import WARSAW, route_identity  # noqa: E402
from custom_components.nordexpress.sensor import async_setup_entry as setup_sensors  # noqa: E402


def entry_from(result, unique_id):
    return ConfigEntry(
        domain="nordexpress",
        title=result["title"],
        data=result["data"],
        options={},
        unique_id=unique_id,
        version=1,
        minor_version=1,
        source="user",
        discovery_keys=MappingProxyType({}),
        subentries_data=(),
    )


async def flow_for(hass, lines, choices):
    flow = NordExpressConfigFlow()
    flow.hass = hass
    flow.context = {"source": "user"}
    flow.flow_id = "smoke-flow"
    assert (await flow.async_step_user())["step_id"] == "user"
    assert (await flow.async_step_user({"stop_id": "1301410:1360673"}))["step_id"] == "line"
    step = await flow.async_step_line({"lines": lines})
    for line in sorted(lines):
        assert step["description_placeholders"]["line"] == line
        step = await flow.async_step_direction({"directions": choices[line]})
    return step


async def main():
    with tempfile.TemporaryDirectory(prefix="nordexpress-ha-") as config_dir:
        hass = HomeAssistant(config_dir)
        hass.config_entries = ConfigEntries(hass, {})
        await hass.config_entries.async_initialize()
        api = AsyncMock()
        api.stops.return_value = [
            {
                "id": "1301410:1360673",
                "name": "Główczyce",
                "number": 51,
                "latitude": 54.619418,
                "longitude": 17.374931,
            }
        ]
        api.directions.return_value = [{"line": "101"}, {"line": "105"}]

        def schedule(stop, line, day):
            return {
                "departures": [
                    {"departure": 36000, "trip_id": 1, "index": 0, "symbols": ""},
                    {"departure": 39600, "trip_id": 2, "index": 0, "symbols": "A"},
                    {"departure": 43200, "trip_id": 3, "index": 0, "symbols": "B"},
                ],
                "main_direction": {"name": "Główczyce"},
                "directions": [
                    {"symbol": "A", "name": "Cecenowo" if line == "105" else "Izbica"},
                    {"symbol": "B", "name": "Słupsk"},
                ],
            }

        api.timetable.side_effect = schedule
        api.departures.side_effect = lambda stop: {
            "rows": [],
            "timestamp": datetime.now(WARSAW).timestamp(),
        }
        hass.data["nordexpress"] = api
        choices = {"101": ["Główczyce"], "105": ["Główczyce", "Cecenowo"]}
        result = await flow_for(hass, ["105", "101"], choices)
        assert set(result["data"]["routes"]) == {"101", "105"}
        entry = entry_from(result, "group-a")
        hass.config_entries._entries[entry.entry_id] = entry
        coords = {line: NordExpressCoordinator(hass, api, entry, line) for line in choices}
        for coord in coords.values():
            coord.data = await coord._async_update_data()
        entry.runtime_data = coords
        sensors, calendars = [], []
        await setup_sensors(hass, entry, sensors.extend)
        await setup_calendars(hass, entry, calendars.extend)
        assert len(sensors) == len(calendars) == 2
        assert len({sensor.unique_id for sensor in sensors}) == 2
        sensor105 = next(
            sensor for sensor in sensors if sensor.extra_state_attributes["line"] == "105"
        )
        attrs = sensor105.extra_state_attributes
        assert sensor105.name == "Linia 105 - Główczyce"
        assert {attrs["Direction"], attrs["NextBusDirection"]} == {"Główczyce", "Cecenowo"}
        assert all(row["direction"] != "Słupsk" for row in attrs["departures"])
        now = datetime.now(WARSAW)
        cal105 = next(cal for cal in calendars if cal.extra_state_attributes["line"] == "105")
        events = await cal105.async_get_events(hass, now, now + timedelta(days=2))
        assert {event.summary for event in events} == {
            "Linia 105 → Główczyce",
            "Linia 105 → Cecenowo",
        }
        # Same physical stop and same line can be added as an independent opposite direction.
        opposite = await flow_for(hass, ["105"], {"105": ["Słupsk"]})
        assert "data" in opposite and opposite["data"]["routes"] == {"105": ["Słupsk"]}
        duplicate = await flow_for(hass, ["101", "105"], choices)
        assert duplicate["reason"] == "already_configured"
        options = NordExpressOptionsFlow()
        options.hass, options.handler, options.context, options.flow_id = (
            hass,
            entry.entry_id,
            {},
            "smoke-options",
        )
        assert (await options.async_step_init())["step_id"] == "init"
        assert (await options.async_step_init({"lines": ["105"], "calendar_days": 3}))[
            "step_id"
        ] == "direction"
        assert (await options.async_step_direction({"directions": []}))["errors"]
        updated = await options.async_step_direction({"directions": ["Główczyce", "Cecenowo"]})
        assert set(updated["data"]["routes"]) == {"105"}
        assert entry.unique_id == "group-a"
        dr.async_setup(hass)
        await dr.async_load(hass)
        await er.async_load(hass)
        registry = er.async_get(hass)
        active = [
            registry.async_get_or_create(
                "sensor", "nordexpress", sensor.unique_id, config_entry=entry
            ).entity_id
            for sensor in sensors
        ]
        active += [
            registry.async_get_or_create(
                "calendar", "nordexpress", cal.unique_id, config_entry=entry
            ).entity_id
            for cal in calendars
        ]
        obsolete = [
            registry.async_get_or_create(
                "sensor", "nordexpress", f"group-a_{key}", config_entry=entry
            ).entity_id
            for key in ("following_departure", "minutes_until_departure", "999_next_departure")
        ]
        obsolete.append(
            registry.async_get_or_create(
                "calendar",
                "nordexpress",
                "group-a_999_calendar",
                config_entry=entry,
            ).entity_id
        )
        custom = registry.async_get_or_create(
            "sensor", "nordexpress", "group-a_custom", config_entry=entry
        ).entity_id
        foreign = registry.async_get_or_create(
            "sensor", "other_platform", "group-a_following_departure", config_entry=entry
        ).entity_id
        async_remove_obsolete_sensors(hass, entry)
        assert all(registry.async_get(entity_id) is None for entity_id in obsolete)
        assert all(
            registry.async_get(entity_id) is not None for entity_id in [*active, custom, foreign]
        )
        async_remove_obsolete_sensors(hass, entry)
        legacy = entry_from(
            {
                "title": "Legacy",
                "data": {
                    "stop_id": "1301410:1360673",
                    "stop_name": "Główczyce",
                    "line": "105",
                    "direction": "Główczyce",
                },
            },
            "legacy-id",
        )
        legacy_coord = NordExpressCoordinator(hass, api, legacy)
        assert legacy_coord.config["line"] == "105"
        assert route_identity(legacy.data, legacy.unique_id, "105") == "legacy-id"
        for coord in [*coords.values(), legacy_coord]:
            await coord.async_shutdown()
        await hass.async_stop(force=True)
        print(
            "HA runtime smoke: line selection, independent directions, one sensor/calendar per line, options and registry cleanup OK"
        )


if __name__ == "__main__":
    asyncio.run(main())

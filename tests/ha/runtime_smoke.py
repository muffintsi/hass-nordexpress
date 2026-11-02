"""Run real HA classes without the Unix-only pytest harness.

Run from repository root: python tests/ha/runtime_smoke.py
Requires Home Assistant installed in an isolated environment. No HA server is
started and no public network requests are made.
"""

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

from custom_components.nordexpress.calendar import NordExpressCalendar  # noqa: E402
from custom_components.nordexpress.config_flow import NordExpressConfigFlow, NordExpressOptionsFlow  # noqa: E402
from custom_components.nordexpress.coordinator import NordExpressCoordinator  # noqa: E402
from custom_components.nordexpress.model import WARSAW  # noqa: E402
from custom_components.nordexpress.sensor import NordExpressSensor  # noqa: E402


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
        api.directions.return_value = [{"line": "105"}]
        api.timetable.return_value = {
            "departures": [
                {"departure": 36000, "trip_id": 1, "index": 0, "symbols": ""},
                {"departure": 39600, "trip_id": 2, "index": 0, "symbols": "A"},
            ],
            "main_direction": {"name": "Słupsk"},
            "directions": [{"symbol": "A", "name": "Cecenowo"}],
        }
        api.departures.return_value = {"rows": [], "timestamp": datetime.now(WARSAW).timestamp()}
        hass.data["nordexpress"] = api
        flow = NordExpressConfigFlow()
        flow.hass = hass
        flow.context = {"source": "user"}
        flow.flow_id = "runtime-smoke"
        assert (await flow.async_step_user())["step_id"] == "user"
        assert (await flow.async_step_user({"stop_id": "1301410:1360673"}))["step_id"] == "line"
        assert (await flow.async_step_line({"line": "105"}))["step_id"] == "direction"
        result = await flow.async_step_direction({"directions": ["Słupsk", "Cecenowo"]})
        entry = ConfigEntry(
            domain="nordexpress",
            title=result["title"],
            data=result["data"],
            options={},
            unique_id="1301410:1360673|105|Słupsk",
            version=1,
            minor_version=1,
            source="user",
            discovery_keys=MappingProxyType({}),
            subentries_data=(),
        )
        hass.config_entries._entries[entry.entry_id] = entry
        options = NordExpressOptionsFlow()
        options.hass = hass
        options.handler = entry.entry_id
        options.context = {}
        options.flow_id = "runtime-options"
        assert (await options.async_step_init())["step_id"] == "init"
        invalid = await options.async_step_init({"directions": [], "calendar_days": 7})
        assert invalid["errors"]["directions"] == "invalid_selection"
        updated = await options.async_step_init({"directions": ["Słupsk"], "calendar_days": 3})
        assert updated["data"]["directions"] == ["Słupsk"]
        assert entry.unique_id == "1301410:1360673|105|Słupsk"
        coordinator = NordExpressCoordinator(hass, api, entry)
        coordinator.data = await coordinator._async_update_data()
        entry.runtime_data = coordinator
        sensors = [
            NordExpressSensor(entry, key, index)
            for key, index in (
                ("next_departure", 0),
                ("following_departure", 1),
                ("minutes_until_departure", 0),
            )
        ]
        for sensor in sensors:
            assert sensor.native_value is not None
        attrs = sensors[0].extra_state_attributes
        assert {attrs["Direction"], attrs["NextBusDirection"]} == {"Słupsk", "Cecenowo"}
        assert attrs["BusHour"] in ("10:00", "11:00")
        assert attrs["realtime_available"] is True
        calendar = NordExpressCalendar(entry)
        assert calendar.event is not None
        now = datetime.now(WARSAW)
        events = await calendar.async_get_events(hass, now, now + timedelta(days=2))
        assert {event.summary for event in events} == {"Linia 105 → Słupsk", "Linia 105 → Cecenowo"}
        assert (
            await calendar.async_get_events(
                hass, now + timedelta(days=20), now + timedelta(days=22)
            )
            == []
        )
        await coordinator.async_shutdown()
        legacy_data = {key: value for key, value in entry.data.items() if key != "directions"}
        legacy_data["direction"] = "Słupsk"
        legacy = ConfigEntry(
            domain="nordexpress",
            title="Legacy single destination",
            data=legacy_data,
            options={"directions": ["Słupsk", "Cecenowo"]},
            unique_id="legacy-id",
            version=1,
            minor_version=1,
            source="user",
            discovery_keys=MappingProxyType({}),
            subentries_data=(),
        )
        legacy_coordinator = NordExpressCoordinator(hass, api, legacy)
        assert legacy_coordinator.config["directions"] == ["Cecenowo", "Słupsk"]
        await legacy_coordinator.async_shutdown()
        await hass.async_stop(force=True)
        print("HA runtime smoke: config forms, coordinator, 3 sensors, calendar OK")


if __name__ == "__main__":
    asyncio.run(main())

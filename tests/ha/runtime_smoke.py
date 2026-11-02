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
from custom_components.nordexpress.config_flow import NordExpressConfigFlow  # noqa: E402
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
                {"departure": 39600, "trip_id": 2, "index": 0, "symbols": ""},
            ],
            "main_direction": {"name": "Słupsk"},
            "directions": [],
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
        result = await flow.async_step_direction({"direction": "Słupsk"})
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
        assert attrs["Direction"] == "Słupsk"
        assert attrs["BusHour"] in ("10:00", "11:00")
        assert attrs["realtime_available"] is True
        calendar = NordExpressCalendar(entry)
        assert calendar.event is not None
        now = datetime.now(WARSAW)
        events = await calendar.async_get_events(hass, now, now + timedelta(days=2))
        assert events and events[0].summary == "Linia 105 → Słupsk"
        assert (
            await calendar.async_get_events(
                hass, now + timedelta(days=20), now + timedelta(days=22)
            )
            == []
        )
        await coordinator.async_shutdown()
        await hass.async_stop(force=True)
        print("HA runtime smoke: config forms, coordinator, 3 sensors, calendar OK")


if __name__ == "__main__":
    asyncio.run(main())

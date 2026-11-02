"""Exercise actual HA flows, platform setup, calendar and unload."""

from datetime import datetime, timedelta, timezone

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType


@pytest.mark.asyncio
async def test_config_flow(hass, api):
    result = await hass.config_entries.flow.async_init("nordexpress", context={"source": "user"})
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"stop_id": "1301410:1360673"}
    )
    assert result["step_id"] == "line"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"lines": ["105"]})
    assert result["step_id"] == "direction"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"directions": ["Słupsk"]}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["stop_code"] == "51"
    assert result["data"]["latitude"] == 54.619418
    await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_duplicate_relation(hass, api, entry):
    result = await hass.config_entries.flow.async_init("nordexpress", context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"stop_id": "1301410:1360673"}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"lines": ["105"]})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"directions": ["Słupsk"]}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.asyncio
async def test_platforms_calendar_options_and_unload(hass, api, entry):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.LOADED
    sensors = hass.states.async_all("sensor")
    assert len(sensors) == 1
    main = next(state for state in sensors if "BusHour" in state.attributes)
    assert main.attributes["Direction"] == "Słupsk"
    assert main.attributes["BusHour"] in {"10:00", "11:00"}
    assert main.attributes["latitude"] == 54.619418
    assert main.attributes["realtime_available"] is True
    calendars = hass.states.async_all("calendar")
    assert len(calendars) == 1
    assert calendars[0].attributes["calendar_days"] == 7
    now = datetime.now(timezone.utc)
    result = await hass.services.async_call(
        "calendar",
        "get_events",
        {
            "entity_id": calendars[0].entity_id,
            "start_date_time": now.isoformat(),
            "end_date_time": (now + timedelta(days=2)).isoformat(),
        },
        blocking=True,
        return_response=True,
    )
    events = result[calendars[0].entity_id]["events"]
    assert events
    assert events[0]["summary"] == "Linia 105 → Słupsk"
    options = await hass.config_entries.options.async_init(entry.entry_id)
    assert options["step_id"] == "init"
    options = await hass.config_entries.options.async_configure(
        options["flow_id"], {"calendar_days": 3}
    )
    assert options["step_id"] == "direction"
    options = await hass.config_entries.options.async_configure(
        options["flow_id"], {"directions": ["Słupsk"]}
    )
    assert options["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options["calendar_days"] == 3
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.NOT_LOADED


@pytest.mark.asyncio
async def test_live_failure_falls_back_to_schedule(hass, api, entry):
    from custom_components.nordexpress.api import NordExpressError

    api.departures.side_effect = NordExpressError("offline")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    main = next(state for state in hass.states.async_all("sensor") if "BusHour" in state.attributes)
    assert main.state not in {"unavailable", "unknown"}
    assert main.attributes["realtime_available"] is False


@pytest.mark.asyncio
async def test_schedule_failure_retries_setup(hass, api, entry):
    from custom_components.nordexpress.api import NordExpressError

    api.timetable.side_effect = NordExpressError("offline")
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.SETUP_RETRY

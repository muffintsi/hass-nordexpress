"""Real Home Assistant fixtures (Linux CI)."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def api(hass):
    from custom_components.nordexpress.model import WARSAW

    client = AsyncMock()
    client.stops.return_value = [
        {
            "id": "1301410:1360673",
            "name": "Główczyce",
            "number": 51,
            "latitude": 54.619418,
            "longitude": 17.374931,
        },
    ]
    client.directions.return_value = [{"line": "105", "direction": "Słupsk"}]
    client.timetable.return_value = {
        "departures": [
            {"departure": 36000, "trip_id": 1, "index": 0, "symbols": ""},
            {"departure": 39600, "trip_id": 2, "index": 0, "symbols": ""},
        ],
        "main_direction": {"name": "Słupsk"},
        "directions": [],
        "platform": "1",
    }
    client.departures.side_effect = lambda stop: {
        "rows": [],
        "directions": {},
        "timestamp": datetime.now(WARSAW).timestamp(),
    }
    hass.data["nordexpress"] = client
    return client


@pytest.fixture
def entry(hass):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain="nordexpress",
        title="Główczyce · 105 → Słupsk",
        version=1,
        unique_id="1301410:1360673|105|Słupsk",
        data={
            "stop_id": "1301410:1360673",
            "stop_name": "Główczyce",
            "stop_code": "51",
            "latitude": 54.619418,
            "longitude": 17.374931,
            "line": "105",
            "direction": "Słupsk",
        },
    )
    entry.add_to_hass(hass)
    return entry

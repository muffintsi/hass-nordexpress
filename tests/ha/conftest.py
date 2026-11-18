"""Real Home Assistant fixtures (Linux CI)."""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations, monkeypatch):
    import custom_components

    # The HA harness also ships a custom_components package. Include this
    # checkout explicitly so both direct imports and HA discovery find it.
    component_path = str(Path(__file__).resolve().parents[2] / "custom_components")
    monkeypatch.setattr(
        custom_components, "__path__", [component_path, *custom_components.__path__]
    )
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

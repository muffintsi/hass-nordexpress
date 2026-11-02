"""One ZIM-compatible departure sensor per configured relation."""

from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BASE_URL, DOMAIN
from .model import WARSAW, route_identity, upcoming
from .presentation import zim_attributes


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [NordExpressSensor(entry, coordinator) for coordinator in entry.runtime_data.values()]
    )


class NordExpressSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = False
    _attr_icon = "mdi:bus"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, entry, coordinator):
        super().__init__(coordinator)
        line = coordinator.config["line"]
        identity = route_identity(entry.data, entry.unique_id, line)
        # Keep the main sensor identity from 0.1/0.2 for existing cards.
        self._attr_unique_id = f"{identity}_next_departure"
        self._attr_name = f"Linia {line} - {entry.data['stop_name']}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, identity)},
            "name": f"{self.coordinator.config['stop_name']} · {line} → {self.coordinator.config['direction']}",
            "manufacturer": "Nord Express / kiedyPrzyjedzie.pl",
            "entry_type": DeviceEntryType.SERVICE,
            "configuration_url": f"{BASE_URL}/#/stops/{entry.data['stop_id']}/departures",
        }

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._tick,
                timedelta(seconds=15),
            )
        )

    @callback
    def _tick(self, _now):
        self.async_write_ha_state()

    def _upcoming(self):
        if not self.coordinator.data:
            return []
        return upcoming(
            self.coordinator.data["departures"],
            self.coordinator.config["directions"],
            datetime.now(WARSAW),
        )

    @property
    def native_value(self):
        departures = self._upcoming()
        return departures[0].when if departures else None

    @property
    def extra_state_attributes(self):
        return zim_attributes(self._upcoming(), self.coordinator.config)

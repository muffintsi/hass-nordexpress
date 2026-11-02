"""Next two departures and a locally refreshed countdown."""

import math
from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTime
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BASE_URL, DOMAIN
from .model import WARSAW, instant, upcoming
from .presentation import zim_attributes


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [
            NordExpressSensor(entry, "next_departure", 0),
            NordExpressSensor(entry, "following_departure", 1),
            NordExpressSensor(entry, "minutes_until_departure", 0),
        ]
    )


class NordExpressSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:bus-clock"

    def __init__(self, entry, key, index):
        super().__init__(entry.runtime_data)
        self.key = key
        self.index = index
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.unique_id}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.unique_id)},
            "name": entry.title,
            "manufacturer": "Nord Express / kiedyPrzyjedzie.pl",
            "entry_type": DeviceEntryType.SERVICE,
            "configuration_url": f"{BASE_URL}/#/stops/{entry.data['stop_id']}/departures",
        }
        if key == "minutes_until_departure":
            self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
            self._attr_device_class = SensorDeviceClass.DURATION
        else:
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        if key == "next_departure":
            self._attr_has_entity_name = False
            self._attr_name = (
                f"Linia {entry.data['line']} - {entry.data['stop_name']}"
                f" → {entry.data['direction']} (Nord Express)"
            )
            self._attr_icon = "mdi:bus"

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
            self.coordinator.config["direction"],
            datetime.now(WARSAW),
        )

    @property
    def native_value(self):
        departures = self._upcoming()
        if len(departures) <= self.index:
            return None
        when = departures[self.index].when
        if self.key == "minutes_until_departure":
            return max(
                0, math.ceil((instant(when) - instant(datetime.now(WARSAW))).total_seconds() / 60)
            )
        return when

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        departures = self._upcoming()
        attrs = {
            "stop_id": self.coordinator.config["stop_id"],
            "line": self.coordinator.config["line"],
            "direction": self.coordinator.config["direction"],
            "realtime_available": data.get("realtime_available", False),
            "horizon_end": data.get("horizon_end"),
        }
        if self.key == "next_departure":
            attrs.update(zim_attributes(departures, self.coordinator.config))
            attrs["departures"] = [item.as_dict() for item in departures[:10]]
            attrs["canceled_departures"] = data.get("canceled", [])[:10]
            attrs["realtime_timestamp"] = data.get("realtime_timestamp")
        if len(departures) > self.index:
            attrs.update(departures[self.index].as_dict())
        return attrs

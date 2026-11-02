"""Nord Express integration."""

from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NordExpressApi
from .const import DOMAIN
from .coordinator import NordExpressCoordinator

PLATFORMS = [Platform.SENSOR, Platform.CALENDAR]


def get_api(hass):
    """One API/cache per HA instance, shared by configuration and all entries."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = NordExpressApi(async_get_clientsession(hass))
    return hass.data[DOMAIN]


async def async_setup_entry(hass, entry):
    coordinator = NordExpressCoordinator(hass, get_api(hass), entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)

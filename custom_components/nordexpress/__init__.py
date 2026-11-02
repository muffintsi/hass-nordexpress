"""Nord Express integration."""

from homeassistant.const import Platform
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NordExpressApi
from .const import DOMAIN
from .coordinator import NordExpressCoordinator
from .model import configured_routes, route_identity

PLATFORMS = [Platform.SENSOR, Platform.CALENDAR]


def get_api(hass):
    """One API/cache per HA instance, shared by configuration and all entries."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = NordExpressApi(async_get_clientsession(hass))
    return hass.data[DOMAIN]


async def async_setup_entry(hass, entry):
    coordinators = {}
    for line in configured_routes(entry.data, entry.options):
        coordinator = NordExpressCoordinator(hass, get_api(hass), entry, line)
        await coordinator.async_config_entry_first_refresh()
        coordinators[line] = coordinator
    entry.runtime_data = coordinators
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    async_remove_obsolete_sensors(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


@callback
def async_remove_obsolete_sensors(hass, entry):
    """Remove retired helper sensors and deselected lines owned by this entry."""
    registry = er.async_get(hass)
    active = set()
    for line in configured_routes(entry.data, entry.options):
        identity = route_identity(entry.data, entry.unique_id, line)
        active.update((f"{identity}_next_departure", f"{identity}_calendar"))
    known_suffixes = (
        "_following_departure",
        "_minutes_until_departure",
        "_next_departure",
        "_calendar",
    )
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if (
            entity.domain in ("sensor", "calendar")
            and entity.platform == DOMAIN
            and entity.unique_id.startswith(f"{entry.unique_id}_")
            and entity.unique_id.endswith(known_suffixes)
            and entity.unique_id not in active
        ):
            registry.async_remove(entity.entity_id)

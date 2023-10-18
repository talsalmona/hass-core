"""The Israel Red Alert integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> bool:
    """Set up Israel Red Alert from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    api = OrefAPI(entry.data["area"])
    hass.data[DOMAIN][entry.entry_id] = api
    coordinator = RedAlertCoordinator(hass, api)

    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        RedAlertEntity(coordinator, idx) for idx, ent in enumerate(coordinator.data)
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class OrefAPI:
    """Pikud HaOref API."""

    def __init__(self, area: str) -> None:
        """Set the area."""
        self._area = area

    def fetch_data(self):
        """Return the areas that are triggered."""
        return ["נגבה"]


class RedAlertCoordinator(DataUpdateCoordinator):
    """Red Alert coordinator."""

    def __init__(self, hass: HomeAssistant, api) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Red Alert",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=5),
        )
        self._api = api

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with self.timeout.async_timeout.timeout(10):
                # Grab active context variables to limit data required to be fetched from API
                # Note: using context is not required if there is no need or ability to limit
                # data retrieved from API.
                listening_idx = set(self.async_contexts())
                return await self._api.fetch_data(listening_idx)
        except Exception as e:
            raise UpdateFailed(f"Error communicating with API: {e}") from e


class RedAlertEntity(CoordinatorEntity, BinarySensorEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    def __init__(self, coordinator, idx) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context=idx)
        self.idx = idx

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_on = self.coordinator.data[self.idx]["state"]
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return True if the binary sensor is on."""
        return bool(self._attr_is_on)

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return the class of the binary sensor."""
        return BinarySensorDeviceClass.SAFETY

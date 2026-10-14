"""Integración de Aigües d'Elx."""

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry, ConfigEntryAuthFailed
from homeassistant.core import HomeAssistant

from .api import AigueselxApi
from .coordinator import AigueselxCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "button"]


async def async_setup(
    hass: HomeAssistant,
    config: dict,
) -> bool:
    """Configurar la integración."""
    hass.data.setdefault("aigueselx", {})
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Configurar una entrada."""
    api = AigueselxApi(
        entry.data["usuario"],
        entry.data["password"],
    )

    login_ok = False
    for intento in range(3):
        if await api.async_login():
            login_ok = True
            break

        _LOGGER.warning(
            "Aigües d'Elx: login fallido, reintento %s/3 en 60s",
            intento + 1,
        )
        await asyncio.sleep(60)

    if not login_ok:
        await api.async_close()
        raise ConfigEntryAuthFailed(
            "Las credenciales de Aigües d'Elx no son válidas."
        )

    coordinator = AigueselxCoordinator(
        hass,
        entry,
        api,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data["aigueselx"][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Descargar la integración."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    data = hass.data["aigueselx"].pop(entry.entry_id, None)

    if data is not None:
        await data["api"].async_close()

    return unload_ok
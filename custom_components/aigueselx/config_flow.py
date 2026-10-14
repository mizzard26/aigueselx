"""Flujo de configuración de Aigües d'Elx."""

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
)

from .api import AigueselxApi

_LOGGER = logging.getLogger(__name__)


class AigueselxConfigFlow(
    config_entries.ConfigFlow,
    domain="aigueselx",
):
    """Configurar Aigües d'Elx."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Configuración inicial."""
        errors = {}

        if user_input is not None:
            api = AigueselxApi(
                user_input["usuario"],
                user_input["password"],
            )

            try:
                if await api.async_login():
                    return self.async_create_entry(
                        title="Aigües d'Elx",
                        data=user_input,
                    )

                errors["base"] = "invalid_auth"

            finally:
                await api.async_close()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("usuario"): str,
                    vol.Required("password"): TextSelector(
                        TextSelectorConfig(type="password")
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input=None):
        """Reconfigurar la integración."""
        entry = self._get_reconfigure_entry()
        errors = {}

        if user_input is not None:
            usuario = user_input["usuario"].strip()
            password = user_input["password"].strip()

            if not password:
                errors["base"] = "invalid_auth"
            else:
                # Cerrar la sesión activa antes de validar las nuevas
                # credenciales para evitar logins simultáneos en el portal.
                datos_actuales = self.hass.data.get(
                    "aigueselx", {}
                ).get(entry.entry_id)

                if datos_actuales is not None:
                    try:
                        await datos_actuales["api"].async_close()
                    except Exception as err:
                        _LOGGER.warning(
                            "Aigües d'Elx: no se pudo cerrar la sesión "
                            "activa antes de reconfigurar: %s",
                            err,
                        )

                api = AigueselxApi(usuario, password)
                try:
                    if await api.async_login():
                        return self.async_update_reload_and_abort(
                            entry,
                            data_updates={
                                "usuario": usuario,
                                "password": password,
                            },
                        )
                    errors["base"] = "invalid_auth"
                finally:
                    await api.async_close()

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "usuario",
                        default=entry.data.get("usuario", ""),
                    ): str,
                    vol.Required("password"): TextSelector(
                        TextSelectorConfig(type="password")
                    ),
                }
            ),
            errors=errors,
        )
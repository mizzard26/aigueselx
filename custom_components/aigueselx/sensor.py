
"""Sensores de Aigües d'Elx."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import (
    STATISTIC_ID_HORARIO,
    AigueselxCoordinator,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Crear el sensor horario."""

    coordinator: AigueselxCoordinator = (
        hass.data["aigueselx"][entry.entry_id]["coordinator"]
    )

    async_add_entities([
        AigueselxSensorHorario(coordinator),
    ])


class AigueselxSensorHorario(CoordinatorEntity, SensorEntity):
    """Sensor horario de consumo de agua."""

    _attr_has_entity_name = True
    _attr_name = "Consumo agua horario"
    _attr_unique_id = "aigueselx_horario"
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:timeline-clock-outline"

    def __init__(
        self,
        coordinator: AigueselxCoordinator,
    ) -> None:
        """Inicializar el sensor."""
        super().__init__(coordinator)

    @property
    def native_value(self) -> float | None:
        """Devolver el consumo del último intervalo."""

        datos = self.coordinator.data or {}
        registros = sorted(
            datos.get("horario", []),
            key=lambda r: (
                r.get("fechaConsumo", ""),
                r.get("horaConsumo", ""),
            ),
            reverse=True,
        )

        if not registros:
            return None

        return self._convertir_numero(
            registros[0].get("consumo")
        )

    @property
    def extra_state_attributes(self) -> dict:
        """Devolver la lectura actual del contador."""

        datos = self.coordinator.data or {}
        registros = sorted(
            datos.get("horario", []),
            key=lambda r: (
                r.get("fechaConsumo", ""),
                r.get("horaConsumo", ""),
            ),
            reverse=True,
        )
        registro = registros[0] if registros else {}

        actualizado = datos.get("actualizado")
        ultima_consulta = self.coordinator.ultima_consulta

        return {
            "statistic_id": STATISTIC_ID_HORARIO,
            "lectura_actual": registro.get("lectura"),
            "actualizado": (
                actualizado.isoformat()
                if actualizado is not None
                else None
            ),
            "ultima_consulta": (
                ultima_consulta.isoformat()
                if ultima_consulta is not None
                else None
            ),
        }

    @staticmethod
    def _convertir_numero(valor) -> float | None:
        """Convertir números con formato español."""

        if valor is None:
            return None

        if isinstance(valor, (int, float)):
            return float(valor)

        texto = str(valor).strip()

        if not texto:
            return None

        if "," in texto and "." in texto:
            texto = texto.replace(".", "").replace(",", ".")
        elif "," in texto:
            texto = texto.replace(",", ".")

        try:
            return float(texto)
        except ValueError:
            return None
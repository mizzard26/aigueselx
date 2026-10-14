"""Botones de Aigües d'Elx."""

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import AigueselxCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Crear botones."""
    coordinator: AigueselxCoordinator = (
        hass.data["aigueselx"][entry.entry_id]["coordinator"]
    )

    async_add_entities(
        [AigueselxBotonHistorico(coordinator)]
    )


class AigueselxBotonHistorico(
    CoordinatorEntity,
    ButtonEntity,
):
    """Botón para cargar el histórico completo."""

    _attr_name = "Cargar histórico completo agua"
    _attr_unique_id = "aigueselx_cargar_historico"
    _attr_icon = "mdi:database-import"

    def __init__(
        self,
        coordinator: AigueselxCoordinator,
    ) -> None:
        super().__init__(coordinator)

    @property
    def extra_state_attributes(self) -> dict:
        """Mostrar el progreso de la carga."""
        return {
            "estado": self.coordinator.historico_estado,
            "progreso": self.coordinator.historico_progreso,
            "registros_horarios": (
                self.coordinator.historico_registros_horarios
            ),
            "registros_diarios": (
                self.coordinator.historico_registros_diarios
            ),
            "resultado": (
                self.coordinator.historico_ultimo_resultado
            ),
        }

    async def async_press(self) -> None:
        """Ejecutar la carga histórica."""
        await self.coordinator.async_importar_historico()
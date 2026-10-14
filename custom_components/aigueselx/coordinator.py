"""Coordinador de datos de Aigües d'Elx."""

import asyncio
import logging
from datetime import datetime, timedelta

from homeassistant.components.recorder.statistics import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
    async_add_external_statistics,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import VolumeConverter

from .api import AigueselxApi

_LOGGER = logging.getLogger(__name__)

STATISTIC_ID_HORARIO = "aigueselx:consumo_agua_horario"
STATISTIC_ID_DIARIO = "aigueselx:consumo_agua_diario"
STATISTIC_ID_ACUMULATIVO = "aigueselx:consumo_agua_acumulativo"

MESES = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}


class AigueselxCoordinator(DataUpdateCoordinator):
    """Coordinar las actualizaciones de Aigües d'Elx."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: AigueselxApi,
    ) -> None:
        self.api = api
        self._historico_lock = asyncio.Lock()
        self.historico_estado = "Pendiente"
        self.historico_progreso = ""
        self.historico_registros_horarios = 0
        self.historico_registros_diarios = 0
        self.historico_ultimo_resultado = ""

        super().__init__(
            hass,
            _LOGGER,
            name="Aigües d'Elx",
            update_interval=timedelta(hours=6),
        )

    async def _async_update_data(self) -> dict:
        """Actualizar los últimos tres días sin importar otras estadísticas."""
        try:
            ahora = dt_util.now()
            fecha_inicio = (
                ahora - timedelta(days=2)
            ).strftime("%d/%m/%Y")
            fecha_fin = ahora.strftime("%d/%m/%Y")

            datos_horarios = await self.api.async_get_consumo_horario(
                fecha_inicio,
                fecha_fin,
            )

            datos_diarios = await self.api.async_get_consumo_diario(
                fecha_inicio,
                fecha_fin,
            )

            self._importar_estadisticas(
                datos_horarios,
                STATISTIC_ID_HORARIO,
                "Consumo agua horario",
            )

            # Calcular la hora del último dato disponible.
            ultima_hora = self._ultima_hora(datos_horarios)

            actualizado = dt_util.now()

            _LOGGER.debug(
                "Aigües d'Elx: %s registros horarios y %s diarios "
                "consultados en la actualización automática",
                len(datos_horarios),
                len(datos_diarios),
            )

            return {
                "horario": datos_horarios,
                "diario": datos_diarios,
                "actualizado": actualizado,
                "ultima_hora": ultima_hora,
            }

        except Exception as err:
            # Si ya tenemos datos previos, no rompemos el sensor:
            # mantenemos los datos anteriores y reintentamos en 5 min.
            if self.data is not None:
                _LOGGER.warning(
                    "Aigües d'Elx: fallo en la actualización (%s). "
                    "Se mantienen los datos anteriores y se "
                    "reintentará en 5 minutos.",
                    err,
                )
                return self.data

            # Primer refresh sin datos previos: sí lanzamos el fallo.
            raise UpdateFailed(
                f"No se han podido actualizar los datos: {err}",
                retry_after=300,
            ) from err

    def _ultima_hora(
        self,
        registros: list[dict],
    ) -> datetime | None:
        """Devolver la fecha/hora del registro más reciente."""
        if not registros:
            return None
        fechas = [
            fecha
            for fecha in (
                self._fecha_registro(r) for r in registros
            )
            if fecha is not None
        ]
        if not fechas:
            return None
        return max(fechas)

    async def async_importar_historico(self) -> None:
        """Importar todo el histórico disponible por intervalos de 90 días."""
        async with self._historico_lock:
            self.historico_estado = "En curso"
            self.historico_progreso = "Preparando consultas"
            self.historico_registros_horarios = 0
            self.historico_registros_diarios = 0
            self.historico_ultimo_resultado = ""
            self.async_update_listeners()

            fecha_fin = dt_util.now().date()
            intervalos_vacios = 0
            numero_intervalo = 0

            try:
                while intervalos_vacios < 2:
                    fecha_inicio = fecha_fin - timedelta(days=89)
                    inicio_texto = fecha_inicio.strftime("%d/%m/%Y")
                    fin_texto = fecha_fin.strftime("%d/%m/%Y")

                    numero_intervalo += 1
                    self.historico_progreso = (
                        f"Intervalo {numero_intervalo}: "
                        f"{inicio_texto} – {fin_texto}"
                    )
                    self.async_update_listeners()

                    datos_horarios = (
                        await self.api.async_get_consumo_horario(
                            inicio_texto,
                            fin_texto,
                        )
                    )
                    datos_diarios = (
                        await self.api.async_get_consumo_diario(
                            inicio_texto,
                            fin_texto,
                        )
                    )

                    if not datos_horarios and not datos_diarios:
                        intervalos_vacios += 1
                    else:
                        intervalos_vacios = 0

                    self._importar_estadisticas(
                        datos_horarios,
                        STATISTIC_ID_HORARIO,
                        "Consumo agua horario",
                    )

                    self.historico_registros_horarios += len(datos_horarios)
                    self.historico_registros_diarios += len(datos_diarios)

                    _LOGGER.info(
                        "Aigües d'Elx histórico: %s–%s; "
                        "%s horarios, %s diarios",
                        inicio_texto,
                        fin_texto,
                        len(datos_horarios),
                        len(datos_diarios),
                    )

                    self.async_update_listeners()
                    fecha_fin = fecha_inicio - timedelta(days=1)

                self.historico_estado = "Finalizado"
                self.historico_progreso = (
                    f"{numero_intervalo} intervalos consultados"
                )
                self.historico_ultimo_resultado = (
                    f"Registros recibidos: "
                    f"{self.historico_registros_horarios} horarios y "
                    f"{self.historico_registros_diarios} diarios."
                )

                _LOGGER.info(
                    "Carga histórica finalizada: %s registros horarios "
                    "y %s diarios recibidos",
                    self.historico_registros_horarios,
                    self.historico_registros_diarios,
                )

            except Exception as err:
                self.historico_estado = "Error"
                self.historico_ultimo_resultado = str(err)
                _LOGGER.exception(
                    "Error durante la carga histórica de Aigües d'Elx"
                )
                raise

            finally:
                self.async_update_listeners()

    def _importar_estadisticas(
        self,
        registros: list[dict],
        statistic_id: str,
        nombre: str,
    ) -> None:
        """Importar únicamente la estadística solicitada."""
        if statistic_id != STATISTIC_ID_HORARIO:
            return

        estadisticas = self._crear_estadisticas(registros)
        if not estadisticas:
            return

        metadata = StatisticMetaData(
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name=nombre,
            source="aigueselx",
            statistic_id=STATISTIC_ID_HORARIO,
            unit_class=VolumeConverter.UNIT_CLASS,
            unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        )

        async_add_external_statistics(
            self.hass,
            metadata,
            estadisticas,
        )

    def _crear_estadisticas(
        self,
        registros: list[dict],
    ) -> list[StatisticData]:
        """Crear estadísticas con consumo horario y lectura acumulada."""
        datos_por_fecha: dict[datetime, tuple[float, float]] = {}

        for registro in registros:
            consumo = self._numero(registro.get("consumo"))
            lectura = self._numero(registro.get("lectura"))

            if consumo is None or lectura is None:
                _LOGGER.debug(
                    "Registro horario omitido por falta de consumo o lectura: %s",
                    registro,
                )
                continue

            fecha = self._fecha_registro(registro)
            if fecha is None:
                continue

            fecha = fecha.replace(minute=0, second=0, microsecond=0)
            datos_por_fecha[fecha] = (consumo, lectura)

        return [
            StatisticData(
                start=fecha,
                state=valores[0],
                sum=valores[1],
            )
            for fecha, valores in sorted(datos_por_fecha.items())
        ]

    def _fecha_registro(
        self,
        registro: dict,
    ) -> datetime | None:
        """Convertir la fecha y hora del portal."""
        fecha_texto = str(registro.get("fechaConsumo", "")).strip()
        hora_texto = str(registro.get("horaConsumo", "00:00")).strip()
        partes = fecha_texto.split()

        if len(partes) != 3:
            return None

        try:
            dia = int(partes[0])
            mes = MESES[partes[1].lower()]
            anio = int(partes[2])
            hora, minuto = (
                int(parte)
                for parte in hora_texto.split(":")[:2]
            )

            timezone = dt_util.get_time_zone(self.hass.config.time_zone)

            return datetime(
                anio,
                mes,
                dia,
                hora,
                minuto,
                tzinfo=timezone,
            )

        except (KeyError, TypeError, ValueError):
            _LOGGER.warning(
                "No se pudo interpretar el registro: %s",
                registro,
            )
            return None

    @staticmethod
    def _numero(valor) -> float | None:
        """Convertir números españoles o internacionales."""
        if valor is None:
            return None

        if isinstance(valor, (int, float)):
            return float(valor)

        texto = str(valor).strip()
        if not texto:
            return None

        try:
            if "," in texto and "." in texto:
                texto = texto.replace(".", "").replace(",", ".")
            elif "," in texto:
                texto = texto.replace(",", ".")
            return float(texto)
        except ValueError:
            return None
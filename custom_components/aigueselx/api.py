"""Cliente de comunicación con Aigües d'Elx."""

import logging
import re
from urllib.parse import urljoin

import aiohttp

_LOGGER = logging.getLogger(__name__)

LOGIN_URL = "https://www.aigueselx.com/login"
CONSUMOS_URL = (
    "https://www.aigueselx.com/es/group/aguas-de-elche/mis-consumos"
)
USER_AGENT = "Mozilla/5.0"


class AigueselxApi:
    """Cliente de Aigües d'Elx."""

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self.session: aiohttp.ClientSession | None = None
        self.p_auth: str | None = None

        _LOGGER.debug(
            "Aigües d'Elx: credenciales cargadas. "
            "Tipo de usuario=%s; longitud de usuario=%s; "
            "tipo de contraseña=%s; longitud de contraseña=%s",
            type(username).__name__,
            len(username) if isinstance(username, str) else -1,
            type(password).__name__,
            len(password) if isinstance(password, str) else -1,
        )

    async def async_login(self) -> bool:
        """Iniciar sesión y comprobar acceso."""

        await self.async_close()
        self.session = aiohttp.ClientSession(
            cookie_jar=aiohttp.CookieJar()
        )

        try:
            timeout = aiohttp.ClientTimeout(total=60)

            _LOGGER.warning("Aigües d'Elx: etapa 1, abriendo login")

            async with self.session.get(
                LOGIN_URL,
                headers={"User-Agent": USER_AGENT},
                timeout=timeout,
            ) as response:
                if response.status != 200:
                    _LOGGER.error(
                        "Aigües d'Elx: etapa 1 fallida, HTTP %s",
                        response.status,
                    )
                    return False

                html = await response.text()
                action_match = re.search(
                    r"""<form[^>]+action=["']([^"']+)["']""",
                    html,
                    re.IGNORECASE,
                )

                if not action_match:
                    _LOGGER.error(
                        "Aigües d'Elx: etapa 2 fallida, "
                        "formulario no encontrado"
                    )
                    return False

                action = urljoin(
                    str(response.url),
                    action_match.group(1),
                )

            _LOGGER.warning("Aigües d'Elx: etapa 2 correcta")

            datos_login = {
                "saveLastPath": "false",
                "redirect": "",
                "doActionAfterLogin": "false",
                "_CustomLoginPortlet_lastContract": "",
                "_CustomLoginPortlet_login": self.username,
                "_CustomLoginPortlet_password": self.password,
            }

            async with self.session.post(
                action,
                data=datos_login,
                headers={
                    "Referer": LOGIN_URL,
                    "User-Agent": USER_AGENT,
                },
                timeout=timeout,
                allow_redirects=True,
            ) as response:
                url_final = str(response.url)
                html_respuesta = await response.text()
                cookies = [
                    cookie.key
                    for cookie in self.session.cookie_jar
                ]

                _LOGGER.warning(
                    "Aigües d'Elx: etapa 3, HTTP %s, URL final: %s",
                    response.status,
                    url_final,
                )
                _LOGGER.warning(
                    "Aigües d'Elx: cookies recibidas: %s",
                    cookies,
                )
                if "/login" in url_final:
                    texto = html_respuesta.lower()
                    _LOGGER.debug(
                        "Aigües d'Elx: etapa 3 fallida. "
                        "Sigue en login. "
                        "Contiene formulario: %s; "
                        "menciona contraseña: %s; "
                        "menciona error: %s; "
                        "menciona captcha: %s",
                        bool(
                            re.search(
                                r"<form\b",
                                html_respuesta,
                                re.IGNORECASE,
                            )
                        ),
                        "password" in texto or "contraseña" in texto,
                        "error" in texto or "incorrect" in texto,
                        "captcha" in texto,
                    )
                    return False

                referer = url_final

            _LOGGER.warning("Aigües d'Elx: etapa 4, comprobando consumos")

            async with self.session.get(
                CONSUMOS_URL,
                headers={
                    "Referer": referer,
                    "User-Agent": USER_AGENT,
                },
                timeout=timeout,
            ) as response:
                if response.status != 200:
                    _LOGGER.error(
                        "Aigües d'Elx: etapa 4 fallida, HTTP %s",
                        response.status,
                    )
                    return False

                html = await response.text()
                self.p_auth = self._extract_p_auth(html)

            if self.p_auth is None:
                _LOGGER.error(
                    "Aigües d'Elx: etapa 5 fallida, p_auth no encontrado"
                )
                return False

            _LOGGER.warning(
                "Aigües d'Elx: login completado correctamente"
            )
            return True

        except (aiohttp.ClientError, TimeoutError):
            _LOGGER.exception("Aigües d'Elx: error de conexión")
            return False

    async def async_get_consumo_horario(
        self,
        fecha_inicio: str,
        fecha_fin: str,
    ) -> list[dict]:
        """Obtener consumo horario."""
        return await self._async_get_consumo(
            "buscarConsumosHoraria",
            fecha_inicio,
            fecha_fin,
        )

    async def async_get_consumo_diario(
        self,
        fecha_inicio: str,
        fecha_fin: str,
    ) -> list[dict]:
        """Obtener consumo diario."""
        return await self._async_get_consumo(
            "buscarConsumosDiaria",
            fecha_inicio,
            fecha_fin,
        )

    async def _async_get_consumo(
        self,
        operacion: str,
        fecha_inicio: str,
        fecha_fin: str,
    ) -> list[dict]:
        """Realizar una consulta de consumo."""
        if self.session is None or self.p_auth is None:
            raise RuntimeError("No hay una sesión activa.")

        params = {
            "p_p_id": "MisConsumos",
            "p_p_lifecycle": "2",
            "p_p_state": "normal",
            "p_p_mode": "view",
            "p_p_cacheability": "cacheLevelPage",
            "p_auth": self.p_auth,
            "_MisConsumos_op": operacion,
            "_MisConsumos_fechaInicio": fecha_inicio,
            "_MisConsumos_fechaFin": fecha_fin,
            "_MisConsumos_inicio": "0",
            "_MisConsumos_fin": "2499",
        }

        timeout = aiohttp.ClientTimeout(total=120)

        async with self.session.get(
            CONSUMOS_URL,
            params=params,
            headers={
                "Referer": CONSUMOS_URL,
                "User-Agent": USER_AGENT,
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=timeout,
        ) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"HTTP {response.status} al consultar consumos."
                )
            datos = await response.json(content_type=None)

        if not isinstance(datos, dict):
            raise RuntimeError("Respuesta inesperada del portal.")

        consumos = datos.get("consumos", [])
        if not isinstance(consumos, list):
            raise RuntimeError("Formato de consumos inesperado.")

        return consumos

    @staticmethod
    def _extract_p_auth(html: str) -> str | None:
        """Extraer el token p_auth."""
        match = re.search(
            r"""p_auth[=|&"' ]+([A-Za-z0-9_-]+)""",
            html,
        )
        return match.group(1) if match else None

    async def async_close(self) -> None:
        """Cerrar la sesión."""
        if self.session is not None:
            await self.session.close()
            self.session = None
        self.p_auth = None
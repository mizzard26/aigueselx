# Changelog

Todas las versiones notables de este proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y este proyecto sigue [Versionado Semántico](https://semver.org/lang/es/).

## [1.0.2] - 2026-10-23

### Cambiado

- Los reintentos intermedios del coordinator ahora usan nivel `info` en lugar de `warning`. Los fallos puntuales que se recuperan solos (reintentos 1 a 4) ya no ensucian el log de Home Assistant. Solo se muestra un `warning` si se agotan los reintentos y hay que esperar al siguiente ciclo de 6 horas.

## [1.0.1] - 2026-10-19

### Corregido

- Login antes de cada consulta de consumos (evita 404 por sesión caducada del portal).
- Nocturno: busca la última noche completa hacia atrás (máx. 4 días) para evitar falsos "Falta información".
- Sensores derivados con `for: 60s` para evitar datos a medias tras reiniciar HA.

## [1.0.0] - 2026-10-14

### Añadido

- Versión inicial de la integración.
- Login contra el portal de Aigües d'Elx (scraping con cookies + `p_auth`).
- Descarga del consumo horario de los últimos 3 días.
- Importación como estadísticas externas de Home Assistant (`aigueselx:consumo_agua_horario`).
- Botón para cargar el histórico completo por intervalos de 90 días.
- Reintentos de login al arrancar (3 intentos con 60s entre ellos).
- `retry_after=300` para reintentos silenciosos tras un fallo.
- Ciclo de actualización automática cada 6h.
- Si falla un ciclo y hay datos previos, mantiene el último valor bueno.
- Iconos propios (`brand/icon.png`, `brand/logo.png`).
- Traducciones al español (`translations/es.json`).

### Notas

- El portal de Aigües d'Elx no dispone de API pública. La integración hace scraping del portal autenticado.
- El portal devuelve errores 404 de forma intermitente; la integración los tolera y reintenta cada 5 minutos.

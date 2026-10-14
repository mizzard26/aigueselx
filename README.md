# Aigües d'Elx para Home Assistant

Integración custom de Home Assistant para leer el consumo de agua del portal
[aigueselx.com](https://www.aigueselx.com/), que no dispone de API pública.

La integración hace scraping autenticado del portal (login con cookies +
token `p\_auth`), descarga el consumo horario y lo importa como **estadísticas
externas** de Home Assistant, para que aparezcan en el panel de energía y en
las estadísticas de largo plazo.

## Características

* Login automático contra el portal de Aigües d'Elx.
* Descarga del consumo horario de los últimos 3 días en cada ciclo.
* Importación como `external\_statistics` de HA.
* Botón para cargar el histórico completo por intervalos de 90 días.
* Reintentos de login al arrancar (3 intentos con 60s entre ellos).
* Reintento silencioso cada 5 min si falla un ciclo.
* Ciclo de actualización automática cada 6h.

## Instalación

### Vía HACS (recomendado)

1. En HACS, ve a **Integraciones** → menú de 3 puntos → **Repositorios personalizados**.
2. Añade `https://github.com/mizzard26/aigueselx` como tipo **Integration**.
3. Busca **Aigües d'Elx** en HACS e instálala.
4. Reinicia Home Assistant.

### Manual

1. Copia la carpeta `custom\_components/aigueselx/` a tu carpeta `config/custom\_components/`.
2. Reinicia Home Assistant.

## Configuración

1. Ve a **Ajustes → Dispositivos y servicios → Añadir integración**.
2. Busca **Aigües d'Elx**.
3. Introduce tu usuario y contraseña del portal.

## Entidades expuestas

* `sensor.consumo\_agua\_horario` — último registro horario disponible.
* `button.cargar\_historico\_completo\_agua` — fuerza la carga del histórico completo.

El resto de sensores que puedas ver en una instalación real
(`consumo\_agua\_ultimo\_dia\_completo`, `consumo\_agua\_media\_ultimos\_7\_dias`,
`estado\_consumo\_agua\_nocturno`) **no los da esta integración**: son sensores
derivados calculados a partir de las estadísticas externas con
`recorder.get\_statistics`.

## Cómo funciona

1. Al arrancar, la integración hace login en el portal.
2. Cada 6h consulta el consumo horario de los últimos 3 días.
3. Los datos se importan como estadísticas externas en `aigueselx:consumo\_agua\_horario`.
4. Cualquier sensor derivado (día completo, media, nocturno) puede construirse
consultando esas estadísticas.

## Créditos

Desarrollado por [@mizzard26](https://github.com/mizzard26).

## Licencia

MIT


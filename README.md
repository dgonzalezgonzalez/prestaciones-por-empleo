# Prestaciones por desempleo SEPE

Pipeline en Python para descargar y transformar los informes mensuales de prestaciones por desempleo del SEPE.

## Qué hace

- Lee la página oficial del SEPE y detecta todos los Excel mensuales publicados.
- Descarga solo ficheros nuevos o modificados.
- Guarda los Excel originales en `data/raw/`.
- Guarda la caché de descargas en `data/manifest.json`.
- Procesa las hojas:
  - `BP-2.1a`, `BP-2.1b`, `BP-2.1c`
  - `BP-3.1a`, `BP-3.1b`, `BP-3.1c`
  - `BP-3.5a`, `BP-3.5b`, `BP-3.5c`
  - `TC-1.1a`, `TC-1.1b`, `TC-1.1c`
- Genera una base en formato ancho, en español.
- Genera figuras de evolución nacional de prestaciones, beneficiarios y tasa de cobertura.

## Instalación

Este ordenador no usa entornos virtuales. Instala las dependencias en el Python de usuario:

```powershell
py -m pip install --user -r requirements.txt
```

## Ejecución

Descargar y procesar todo:

```powershell
py main.py
```

Procesar solo los ficheros ya descargados:

```powershell
py main.py --no-download
```

Prueba rápida con pocos ficheros:

```powershell
py main.py --limit 1
```

Limitar años:

```powershell
py main.py --from-year 2024 --to-year 2026
```

## Salidas

- `data/raw/Informe-YYYYMM.xlsx`: Excel originales descargados.
- `data/manifest.json`: URL, hash, tamaño, cabeceras y ruta local.
- `data/processed/sepe_prestaciones_wide.csv`: tabla ancha principal, similar a `Libro1.xlsx`, con desagregación por tramos de edad cuando existe en los Excel originales.
- `data/processed/sepe_prestaciones_wide.xlsx`: versión Excel de la tabla ancha principal.
- `Gráficos/evolucion_beneficiarios_tasa_cobertura.svg` y `.png`: beneficiarios de prestación contributiva, subsidios, total de beneficiarios y tasa de cobertura, en formato AIReF.
- `Gráficos/composicion_beneficiarios_prestaciones.svg` y `.png`: composición del total nacional por prestación contributiva y subsidios, en formato AIReF.
- `Gráficos/indice_beneficiarios_tasa_cobertura.svg` y `.png`: comparación indexada entre total de beneficiarios y tasa de cobertura, en formato AIReF.
- `Gráficos/perfil_edad_beneficiarios.svg` y `.png`: perfil nacional por edad de beneficiarios de prestación contributiva y subsidios, en formato AIReF.
- `Gráficos/peso_beneficiarias_por_sexo.svg` y `.png`: peso relativo de mujeres y hombres en el total de beneficiarios, en formato AIReF.
- `Gráficos/tasa_cobertura_ccaa_ultimo_periodo.svg` y `.png`: heterogeneidad territorial de la tasa de cobertura en el último periodo disponible, en formato AIReF.
- `Gráficos/dispersion_ccaa_beneficiarios.svg` y `.png`: rango territorial de la evolución indexada de beneficiarios por comunidad autónoma, en formato AIReF.
- `data/figure_workbooks/*.xlsx`: libros auxiliares con título en `B2`, fuente en `B3`, nota en `B4` y tabla de datos desde `D5`.
- `data/interactive/tasa_cobertura_ccaa_ultimo_periodo.html`: versión interactiva de la tasa de cobertura por comunidad autónoma, con selector anual, eje fijo y referencia de España.
- `data/interactive/perfil_edad_beneficiarios.html`: versión interactiva del perfil por edad, con selector anual, eje fijo y desglose por prestación contributiva y subsidios.
- `data/interactive/peso_subsidios_ccaa.html`: versión interactiva del peso de subsidios en el total de beneficiarios por comunidad autónoma, con selector anual, eje fijo y referencia de España.
- `data/interactive/peso_mujeres_por_edad.html`: versión interactiva del peso de mujeres por tramo de edad, con selector anual y eje fijo de 0 a 100.
- `data/interactive/mapa_calor_tasa_cobertura_ccaa.html`: mapa de calor interactivo de la tasa de cobertura por comunidad autónoma y año, con escala fija.

La tabla ancha empieza con:

- `mes`
- `año`
- `sexo`
- `provincia`
- `edad`
- `comunidad autonoma`
- `nivel geografico`

Después aparecen variables como:

- `total prestacion contributiva`
- `total subsidios de desempleo`
- `subsidios de desempleo de mayores`
- `subsidio de desempleo por agotamiento de la prestacion contributiva`
- `subsidio de desempleo por no cotizacion suficiente`
- `subsidio de desempleo por no cotizacion suficiente - derecho de 3 a 5 meses`
- `subsidio de desempleo por no cotizacion suficiente - derecho de 6 meses`
- `subsidio de desempleo por no cotizacion suficiente - derecho de 21 meses`
- `subsidio de desempleo para emigrantes retornados`
- `subsidio de desempleo para liberados de prision`
- `subsidio de desempleo por revision de invalidez`
- `subsidio de desempleo para fijos discontinuos`
- `subsidio extraordinario por desempleo (SED)`
- `subsidio VVGS`
- `complemento de apoyo al empleo (CAE)`
- `tasa de cobertura`

La tabla principal incluye los tramos de edad de las hojas `BP-2.1` y `BP-3.1`. También incluye filas `Todas las edades` para los desgloses de subsidios por desempleo de las hojas `BP-3.5` y para la tasa de cobertura de `TC-1.1`. Cuando una hoja no cruza edad con tipo de subsidio, esas columnas quedan vacías porque esa desagregación no existe en el Excel original.

## Categorías

- `sexo`: `Ambos sexos`, `Hombres`, `Mujeres`.
- `edad`: tramos de edad y `Todas las edades`.
- `provincia`: provincia, `España`, o `Todas las provincias` para filas agregadas por comunidad autónoma.
- `comunidad autonoma`: comunidad autónoma o `España`.
- `nivel geografico`: `provincia`, `comunidad_autonoma`, `espana`.

El cambio histórico de `Mayores de 55 años` a `Mayores de 52 años` se normaliza como `subsidios de desempleo de mayores`.

## Verificación realizada

Ejecución completa el 2026-05-08:

- 109 Excel procesados.
- Período cubierto: 2017-01 a 2026-03.
- 226.611 filas en tabla ancha principal.
- 12 hojas objetivo detectadas.

Ejecución completa con figuras el 2026-05-11:

- 109 Excel procesados.
- 1.346.234 registros largos procesados internamente.
- 226.611 filas en tabla ancha principal.
- 7 figuras SVG y 7 copias PNG generadas en `Gráficos/`.
- 7 libros auxiliares generados en `data/figure_workbooks/`.
- 5 gráficos interactivos HTML generados en `data/interactive/`.

## Caché de descarga

El proceso de descarga está cacheado:

- Si un Excel ya existe y `ETag`, `Last-Modified` y tamaño coinciden, no se descarga otra vez.
- Si esas cabeceras cambian, el fichero se vuelve a descargar.
- Si el contenido descargado tiene el mismo `sha256`, no se reescribe.
- Si el `sha256` cambia, se actualiza la copia local y `data/manifest.json`.

# Prestaciones por desempleo SEPE

Pipeline en Python para descargar y transformar los informes mensuales de prestaciones por desempleo del SEPE.

## Que hace

- Lee la pagina oficial del SEPE y detecta todos los Excel mensuales publicados.
- Descarga solo ficheros nuevos o modificados.
- Guarda los Excel originales en `data/raw/`.
- Guarda el cache de descargas en `data/manifest.json`.
- Procesa las hojas:
  - `BP-2.1a`, `BP-2.1b`, `BP-2.1c`
  - `BP-3.1a`, `BP-3.1b`, `BP-3.1c`
  - `BP-3.5a`, `BP-3.5b`, `BP-3.5c`
  - `TC-1.1a`, `TC-1.1b`, `TC-1.1c`
- Genera una base en formato largo y otra en formato ancho, en espanol.

## Instalacion

Este ordenador no usa entornos virtuales. Instala dependencias en el Python de usuario:

```powershell
py -m pip install --user -r requirements.txt
```

## Ejecucion

Descargar y procesar todo:

```powershell
py main.py
```

Procesar solo los ficheros ya descargados:

```powershell
py main.py --no-download
```

Prueba rapida con pocos ficheros:

```powershell
py main.py --limit 1
```

Limitar anos:

```powershell
py main.py --from-year 2024 --to-year 2026
```

## Salidas

- `data/raw/Informe-YYYYMM.xlsx`: Excel originales descargados.
- `data/manifest.json`: URL, hash, tamano, cabeceras y ruta local.
- `data/processed/sepe_prestaciones_wide.csv`: tabla ancha principal, similar a `Libro1.xlsx`, filtrada a `Todas las edades`.
- `data/processed/sepe_prestaciones_wide.xlsx`: version Excel de la tabla ancha principal.

La tabla ancha empieza con:

- `mes`
- `año`
- `sexo`
- `provincia`
- `edad`
- `comunidad_autonoma`
- `nivel_geografico`

Despues aparecen variables como:

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

La tabla principal usa `Todas las edades` para evitar una matriz ancha llena de vacios. Incluye los desgloses de subsidios por desempleo de las hojas `BP-3.5`.

## Categorias

- `sexo`: `Ambos sexos`, `Hombres`, `Mujeres`.
- `edad`: tramos de edad y `Todas las edades`.
- `provincia`: provincia, `España`, o `Todas las provincias` para filas agregadas por comunidad autonoma.
- `comunidad_autonoma`: comunidad autonoma o `España`.
- `nivel_geografico`: `provincia`, `comunidad_autonoma`, `espana`.

El cambio historico de `Mayores de 55 años` a `Mayores de 52 años` se normaliza como `subsidios de desempleo de mayores`, conservando el texto original en la tabla larga.

## Verificacion realizada

Ejecucion completa el 2026-05-08:

- 109 Excel procesados.
- Periodo cubierto: 2017-01 a 2026-03.
- 20.601 filas en tabla ancha principal.
- 12 hojas objetivo detectadas.

## Cache de descarga

El proceso de descarga esta cacheado:

- Si un Excel ya existe y `ETag`, `Last-Modified` y tamano coinciden, no se descarga otra vez.
- Si esas cabeceras cambian, el fichero se vuelve a descargar.
- Si el contenido descargado tiene el mismo `sha256`, no se reescribe.
- Si el `sha256` cambia, se actualiza la copia local y `data/manifest.json`.

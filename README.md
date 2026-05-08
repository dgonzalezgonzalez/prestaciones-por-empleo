# SEPE Prestaciones Pipeline

Python pipeline for SEPE unemployment-benefit Excel reports:

- discovers monthly Excel files on the SEPE prestaciones page;
- downloads new or changed files into `data/raw/`;
- stores cache metadata in `data/manifest.json`;
- reshapes selected sheets into long and wide analysis files in `data/processed/`.

## Setup

This machine cannot use virtual environments, so install dependencies into the user Python:

```powershell
py -m pip install --user -r requirements.txt
```

## Run

Full refresh:

```powershell
py main.py
```

Smoke test with one discovered workbook:

```powershell
py main.py --limit 1
```

Process already-downloaded files only:

```powershell
py main.py --no-download
```

Limit year range:

```powershell
py main.py --from-year 2024 --to-year 2026
```

## Outputs

- `data/raw/Informe-YYYYMM.xlsx`: cached source workbooks.
- `data/manifest.json`: source URL, local path, hash, size, and download headers.
- `data/processed/sepe_prestaciones_long.csv`: normalized long table with one value per row.
- `data/processed/sepe_prestaciones_wide.csv`: wide table similar to the provided example workbook.
- `data/processed/sepe_prestaciones_wide.xlsx`: Excel version of the wide table.

Core dimensions:

- `period`, `year`, `month`
- `sex`: `Both`, `Men`, `Women`
- `age_category`, including `All ages`
- `province`, including `Spain` and `All provinces`
- `autonomous_community`, including `Spain`
- `geography_level`: `province`, `autonomous_community`, `spain`, or `unknown`

The parser normalizes the subsidy label change from `Mayores de 55 años` to `Mayores de 52/55 años`, while preserving the original label in long output.

## Source Sheets

Processed sheets:

- `BP-2.1a`, `BP-2.1b`, `BP-2.1c`
- `BP-3.1a`, `BP-3.1b`, `BP-3.1c`
- `BP-3.5a`, `BP-3.5b`, `BP-3.5c`
- `TC-1.1a`, `TC-1.1b`, `TC-1.1c`

The code detects headers by sheet text, not Excel column letters, because SEPE workbook layouts vary over time.


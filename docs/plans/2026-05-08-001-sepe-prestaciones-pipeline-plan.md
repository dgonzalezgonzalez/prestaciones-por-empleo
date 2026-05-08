# SEPE Prestaciones Pipeline Plan

Created: 2026-05-08

## Scope

Build a no-virtualenv Python pipeline that discovers SEPE unemployment-benefit Excel files, downloads new or changed workbooks, and reshapes selected sheets into analysis-ready datasets.

## Requirements

- Discover `.xls`/`.xlsx` links from the SEPE prestaciones page.
- Cache downloads locally and refresh files when remote content changes.
- Process target sheets: `BP-2.1a`, `BP-2.1b`, `BP-2.1c`, `BP-3.1a`, `BP-3.1b`, `BP-3.1c`, `BP-3.5a`, `BP-3.5b`, `BP-3.5c`, `TC-1.1a`, `TC-1.1b`, `TC-1.1c`.
- Avoid hard-coded Excel column letters; infer labels and data extents from sheet contents.
- Keep maximum available disaggregation by sex, age, province, autonomous community, and Spain totals.
- Treat `Mayores de 55 años` and `Mayores de 52 años` as the same subsidy concept, preserving the original label too.
- Provide one master script and README.

## Design

- `main.py` is the run-all entrypoint.
- `src/sepe_pipeline.py` contains discovery, download/cache, parsing, and export logic.
- `data/manifest.json` records discovered files and hashes.
- `data/raw/` stores source workbooks.
- `data/processed/` stores normalized long and wide outputs.

## Verification

- Install user-site dependencies with `py -m pip install --user -r requirements.txt`.
- Run a limited smoke test with one downloaded workbook.
- Validate that processed outputs contain rows from all target sheet families available in the sample.


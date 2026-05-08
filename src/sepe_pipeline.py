from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

import requests
from openpyxl import Workbook


BASE_URL = "https://sepe.es/HomeSepe/que-es-el-sepe/estadisticas/estadisticas-prestaciones/informe-prestaciones.html"
RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
MANIFEST_PATH = Path("data/manifest.json")

TARGET_SHEETS = {
    "BP-2.1a": ("total prestacion contributiva", "Ambos sexos", "age"),
    "BP-2.1b": ("total prestacion contributiva", "Hombres", "age"),
    "BP-2.1c": ("total prestacion contributiva", "Mujeres", "age"),
    "BP-3.1a": ("total subsidios de desempleo", "Ambos sexos", "age"),
    "BP-3.1b": ("total subsidios de desempleo", "Hombres", "age"),
    "BP-3.1c": ("total subsidios de desempleo", "Mujeres", "age"),
    "BP-3.5a": ("total subsidios de desempleo", "Ambos sexos", "subsidy_type"),
    "BP-3.5b": ("total subsidios de desempleo", "Hombres", "subsidy_type"),
    "BP-3.5c": ("total subsidios de desempleo", "Mujeres", "subsidy_type"),
    "TC-1.1a": ("Tasa de cobertura", "Ambos sexos", "coverage"),
    "TC-1.1b": ("Tasa de cobertura", "Hombres", "coverage"),
    "TC-1.1c": ("Tasa de cobertura", "Mujeres", "coverage"),
}

MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

PROVINCE_TO_CCAA = {
    "Almería": "Andalucía", "Cádiz": "Andalucía", "Córdoba": "Andalucía", "Granada": "Andalucía",
    "Huelva": "Andalucía", "Jaén": "Andalucía", "Málaga": "Andalucía", "Sevilla": "Andalucía",
    "Huesca": "Aragón", "Teruel": "Aragón", "Zaragoza": "Aragón",
    "Asturias": "Asturias, Principado de", "Balears, Illes": "Balears, Illes",
    "Palmas, Las": "Canarias", "Santa Cruz de Tenerife": "Canarias",
    "Cantabria": "Cantabria", "Ávila": "Castilla y León", "Burgos": "Castilla y León",
    "León": "Castilla y León", "Palencia": "Castilla y León", "Salamanca": "Castilla y León",
    "Segovia": "Castilla y León", "Soria": "Castilla y León", "Valladolid": "Castilla y León",
    "Zamora": "Castilla y León", "Albacete": "Castilla-La Mancha", "Ciudad Real": "Castilla-La Mancha",
    "Cuenca": "Castilla-La Mancha", "Guadalajara": "Castilla-La Mancha", "Toledo": "Castilla-La Mancha",
    "Barcelona": "Cataluña", "Girona": "Cataluña", "Lleida": "Cataluña", "Tarragona": "Cataluña",
    "Alicante/Alacant": "Comunitat Valenciana", "Castellón/Castelló": "Comunitat Valenciana",
    "Valencia/València": "Comunitat Valenciana", "Badajoz": "Extremadura", "Cáceres": "Extremadura",
    "Coruña, A": "Galicia", "Lugo": "Galicia", "Ourense": "Galicia", "Pontevedra": "Galicia",
    "Madrid": "Madrid, Comunidad de", "Murcia": "Murcia, Región de", "Navarra": "Navarra, Comunidad Foral de",
    "Araba/Álava": "País Vasco", "Bizkaia": "País Vasco", "Gipuzkoa": "País Vasco",
    "Rioja, La": "Rioja, La", "Ceuta": "Ceuta", "Melilla": "Melilla",
}
CCAA_NAMES = set(PROVINCE_TO_CCAA.values())
GEO_ALIASES = {
    "A Coruña": "Coruña, A",
    "La Coruña": "Coruña, A",
    "Las Palmas": "Palmas, Las",
    "Comunidad Valenciana": "Comunitat Valenciana",
    "Navarra, Comunidad Foral": "Navarra, Comunidad Foral de",
    "Illes Balears": "Balears, Illes",
    "Baleares": "Balears, Illes",
    "La Rioja": "Rioja, La",
    "País Vasco": "País Vasco",
}

LONG_FIELDS = [
    "periodo", "año", "mes", "archivo_origen", "url_origen", "hoja_origen",
    "metrica", "variable", "variable_original", "sexo", "edad",
    "nivel_geografico", "provincia", "comunidad_autonoma", "valor",
]


@dataclass(frozen=True)
class RemoteFile:
    url: str
    year: int
    month: int
    filename: str


def norm_text(value) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\n", " ")).strip()


def sheet_key(name: str) -> str:
    return norm_text(name).rstrip(".")


def discover_files(url: str = BASE_URL) -> list[RemoteFile]:
    text = request("GET", url).text
    links = sorted(set(re.findall(r'href=["\']([^"\']+\.xlsx?[^"\']*)["\']', text, flags=re.I)))
    files = []
    for link in links:
        full_url = urljoin(url, link)
        match = re.search(r"(20\d{2})(0[1-9]|1[0-2])", full_url)
        if not match:
            continue
        year, month = int(match.group(1)), int(match.group(2))
        filename = f"Informe-{year}{month:02d}{Path(full_url.split('?')[0]).suffix.lower()}"
        files.append(RemoteFile(full_url, year, month, filename))
    return sorted(files, key=lambda f: (f.year, f.month, f.url))


def request(method: str, url: str, **kwargs) -> requests.Response:
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", "Mozilla/5.0 sepe-prestaciones-pipeline/1.0")
    session = requests.Session()
    session.trust_env = False
    for attempt in range(4):
        try:
            response = session.request(method, url, headers=headers, timeout=60, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {"files": {}}


def save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def download_files(files: list[RemoteFile], limit: int | None = None) -> list[Path]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    paths = []
    selected = files[:limit] if limit else files
    for remote in selected:
        target = RAW_DIR / remote.filename
        entry = manifest["files"].get(remote.url, {})
        if target.exists() and entry.get("sha256"):
            head = try_head(remote.url)
            if head and str(target.stat().st_size) == head.get("content-length", ""):
                paths.append(target)
                continue
        response = request("GET", remote.url)
        digest = sha256_bytes(response.content)
        if target.exists() and entry.get("sha256") == digest:
            paths.append(target)
            continue
        target.write_bytes(response.content)
        manifest["files"][remote.url] = {
            "year": remote.year,
            "month": remote.month,
            "filename": remote.filename,
            "local_path": str(target.as_posix()),
            "source_url": remote.url,
            "sha256": digest,
            "bytes": len(response.content),
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
            "downloaded_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
        paths.append(target)
    save_manifest(manifest)
    return paths


def try_head(url: str) -> dict[str, str] | None:
    try:
        response = request("HEAD", url)
        return {k.lower(): v for k, v in response.headers.items()}
    except requests.RequestException:
        return None


MAX_SCAN_COLS = 80
MAX_SCAN_ROWS = 220


def iter_data_rows(rows: dict[int, list], start_row: int) -> Iterable[tuple[int, list]]:
    blank_count = 0
    for row in range(start_row, MAX_SCAN_ROWS + 1):
        values = rows.get(row, [])
        if not any(v not in (None, "") for v in values):
            blank_count += 1
            if blank_count >= 3:
                break
            continue
        blank_count = 0
        yield row, values


def geography(name: str) -> tuple[str, str, str]:
    name = norm_text(name)
    name = GEO_ALIASES.get(name, name)
    total_names = {"Total Nacional", "TOTAL NACIONAL", "Total", "TOTAL", "España"}
    if name in total_names or name.upper() == "TOTAL NACIONAL":
        return "espana", "España", "España"
    if name in PROVINCE_TO_CCAA:
        return "provincia", name, PROVINCE_TO_CCAA[name]
    if name in CCAA_NAMES:
        return "comunidad_autonoma", "Todas las provincias", name
    return "desconocido", name, "Desconocida"


def clean_variable(label: str) -> str:
    label = norm_text(label)
    label = label.replace("Mayores de 55 años", "Mayores de 52/55 años")
    label = label.replace("Mayores de 52 años", "Mayores de 52/55 años")
    return label


def variable_name(metric: str, original: str, kind: str) -> str:
    label = clean_variable(original).lower()
    if kind in {"age", "coverage"}:
        return metric
    if label == "total":
        return "total subsidios de desempleo"
    if "mayores de 52/55" in label:
        return "subsidios de desempleo de mayores"
    if "agotamiento prestación contributiva" in label:
        return "subsidio de desempleo por agotamiento de la prestacion contributiva"
    if "periodo cotizado insuficiente" in label:
        suffix = ""
        if "derecho de" in label:
            suffix = " - " + label.split(" - ", 1)[-1]
        return "subsidio de desempleo por no cotizacion suficiente" + suffix
    if "emigrantes retornados" in label:
        return "subsidio de desempleo para emigrantes retornados"
    if "liberados de prisión" in label:
        return "subsidio de desempleo para liberados de prision"
    if "fijos discontinuos" in label:
        return "subsidio de desempleo para fijos discontinuos"
    if "plenamente capaces" in label or "inválidos parciales" in label:
        return "subsidio de desempleo por revision de invalidez"
    return clean_variable(original)


def parse_workbook(path: Path, source_url: str | None = None) -> list[dict]:
    match = re.search(r"(20\d{2})(0[1-9]|1[0-2])", path.name)
    if not match:
        raise ValueError(f"Cannot infer period from {path}")
    year, month = int(match.group(1)), int(match.group(2))
    period = f"{year}-{month:02d}"
    workbook = read_xlsx(path)
    sheets = {sheet_key(name): name for name in workbook}
    records = []
    for target, (metric, sex, kind) in TARGET_SHEETS.items():
        sheet_name = sheets.get(target)
        if not sheet_name:
            continue
        rows = workbook[sheet_name]
        if kind == "coverage":
            records.extend(parse_coverage_sheet(rows, path, source_url, period, year, month, target, metric, sex))
        else:
            records.extend(parse_table_sheet(rows, path, source_url, period, year, month, target, metric, sex, kind))
    return records


def parse_table_sheet(rows: dict[int, list], path: Path, source_url: str | None, period: str, year: int, month: int,
                      sheet: str, metric: str, sex: str, kind: str) -> list[dict]:
    header_row = find_row_containing(rows, "Provincias y CC.AA.")
    if not header_row:
        return []
    top = rows.get(header_row - 1, [])
    bottom = rows.get(header_row, [])
    headers = build_headers(top, bottom, kind)
    records = []
    for _, values in iter_data_rows(rows, header_row + 1):
        if len(values) < 3 or not values[1]:
            continue
        geo_level, province, ccaa = geography(values[1])
        for idx, variable in headers.items():
            if idx >= len(values):
                continue
            value = parse_number(values[idx])
            if value is None:
                continue
            original = variable
            age = "Todas las edades"
            if kind == "age":
                age = "Todas las edades" if variable == "TOTAL" else clean_variable(variable)
                variable = metric
            else:
                variable = variable_name(metric, variable, kind)
            records.append(record(period, year, month, path, source_url, sheet, metric, variable,
                                  original, sex, age, geo_level, province, ccaa, value))
    return records


def build_headers(top: list, bottom: list, kind: str) -> dict[int, str]:
    headers = {}
    current_group = None
    max_len = max(len(top), len(bottom))
    for idx in range(2, max_len):
        top_label = norm_text(top[idx] if idx < len(top) else "")
        bottom_label = norm_text(bottom[idx] if idx < len(bottom) else "")
        if top_label and top_label not in {"Tramos de edad"}:
            current_group = top_label
        if kind == "age":
            label = "TOTAL" if top_label == "TOTAL" else bottom_label
        else:
            label = top_label
            if current_group and bottom_label and top_label in {"", current_group}:
                label = f"{current_group} - {bottom_label}"
        if label:
            headers[idx] = label
    return headers


def parse_coverage_sheet(rows: dict[int, list], path: Path, source_url: str | None, period: str, year: int, month: int,
                         sheet: str, metric: str, sex: str) -> list[dict]:
    header_row = find_row_containing(rows, "Provincias y CC.AA.")
    if not header_row:
        return []
    headers = rows.get(header_row, [])
    month_col = None
    for idx, label in enumerate(headers):
        if MONTHS.get(norm_text(label).lower()) == month:
            month_col = idx
            break
    if month_col is None:
        return []
    records = []
    for _, values in iter_data_rows(rows, header_row + 1):
        if len(values) <= month_col or not values[1]:
            continue
        value = parse_number(values[month_col])
        if value is None:
            continue
        geo_level, province, ccaa = geography(values[1])
        records.append(record(period, year, month, path, source_url, sheet, metric, metric,
                              norm_text(headers[month_col]), sex, "Todas las edades", geo_level, province, ccaa, value))
    return records


def find_row_containing(rows: dict[int, list], needle: str) -> int | None:
    for row in range(1, 81):
        if any(norm_text(value) == needle for value in rows.get(row, [])[:20]):
            return row
    return None


def read_xlsx(path: Path) -> dict[str, dict[int, list]]:
    ns = {
        "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    with zipfile.ZipFile(path) as zf:
        shared = read_shared_strings(zf, ns)
        rels = read_workbook_rels(zf, ns)
        root = ET.fromstring(zf.read("xl/workbook.xml"))
        out = {}
        for sheet in root.findall(".//main:sheet", ns):
            name = sheet.attrib["name"]
            if sheet_key(name) not in TARGET_SHEETS:
                continue
            rel_id = sheet.attrib.get(f"{{{ns['rel']}}}id")
            target = rels.get(rel_id)
            if not target:
                continue
            sheet_path = "xl/" + target.lstrip("/")
            out[name] = read_sheet_rows(zf, sheet_path, shared, ns)
        return out


def read_shared_strings(zf: zipfile.ZipFile, ns: dict[str, str]) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    strings = []
    for si in root.findall("main:si", ns):
        parts = [t.text or "" for t in si.findall(".//main:t", ns)]
        strings.append("".join(parts))
    return strings


def read_workbook_rels(zf: zipfile.ZipFile, ns: dict[str, str]) -> dict[str, str]:
    root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rels = {}
    for rel in root.findall("pkgrel:Relationship", ns):
        rels[rel.attrib["Id"]] = rel.attrib["Target"]
    return rels


def read_sheet_rows(zf: zipfile.ZipFile, sheet_path: str, shared: list[str], ns: dict[str, str]) -> dict[int, list]:
    rows = {}
    for event, elem in ET.iterparse(zf.open(sheet_path), events=("end",)):
        if elem.tag.rsplit("}", 1)[-1] != "row":
            continue
        row_idx = int(elem.attrib.get("r", "0"))
        if row_idx > MAX_SCAN_ROWS:
            elem.clear()
            break
        values = []
        for cell in elem:
            if cell.tag.rsplit("}", 1)[-1] != "c":
                continue
            col_idx = column_index(cell.attrib.get("r", "A1"))
            if col_idx > MAX_SCAN_COLS:
                continue
            while len(values) < col_idx:
                values.append(None)
            values[col_idx - 1] = cell_value(cell, shared)
        while values and values[-1] in (None, ""):
            values.pop()
        if values:
            rows[row_idx] = values
        elem.clear()
    return rows


def column_index(ref: str) -> int:
    letters = re.match(r"([A-Z]+)", ref or "A").group(1)
    value = 0
    for char in letters:
        value = value * 26 + ord(char) - 64
    return value


def cell_value(cell, shared: list[str]):
    ctype = cell.attrib.get("t")
    value = cell.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
    if ctype == "inlineStr":
        return "".join(t.text or "" for t in cell.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"))
    if value is None or value.text is None:
        return None
    if ctype == "s":
        return shared[int(value.text)]
    if ctype == "str":
        return value.text
    try:
        number = float(value.text)
        return int(number) if number.is_integer() else number
    except ValueError:
        return value.text


def parse_number(value):
    if value in (None, "", "-"):
        return None
    if isinstance(value, (int, float)):
        return value
    text = norm_text(value).replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def record(period, year, month, path, source_url, sheet, metric, variable, original, sex, age,
           geo_level, province, ccaa, value) -> dict:
    return {
        "periodo": period,
        "año": year,
        "mes": month,
        "archivo_origen": path.name,
        "url_origen": source_url or "",
        "hoja_origen": sheet,
        "metrica": metric,
        "variable": variable,
        "variable_original": original,
        "sexo": sex,
        "edad": age,
        "nivel_geografico": geo_level,
        "provincia": province,
        "comunidad_autonoma": ccaa,
        "valor": value,
    }


def export_records(records: list[dict]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    long_path = PROCESSED_DIR / "sepe_prestaciones_long.csv"
    with long_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=LONG_FIELDS)
        writer.writeheader()
        writer.writerows(records)
    wide_rows = make_wide(records)
    wide_path = PROCESSED_DIR / "sepe_prestaciones_wide.csv"
    if wide_rows:
        key_fields = ["mes", "año", "sexo", "provincia", "edad", "comunidad_autonoma", "nivel_geografico"]
        preferred = [
            "total prestacion contributiva",
            "total subsidios de desempleo",
            "subsidios de desempleo de mayores",
            "subsidio de desempleo por agotamiento de la prestacion contributiva",
            "subsidio de desempleo por no cotizacion suficiente",
            "Tasa de cobertura",
        ]
        value_set = {key for row in wide_rows for key in row if key not in key_fields}
        value_fields = [field for field in preferred if field in value_set]
        value_fields.extend(sorted(value_set - set(value_fields)))
        fields = key_fields + value_fields
        with wide_path.open("w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(wide_rows)
        write_xlsx(wide_rows, PROCESSED_DIR / "sepe_prestaciones_wide.xlsx", fields)


def make_wide(records: list[dict]) -> list[dict]:
    keys = ["mes", "año", "sexo", "provincia", "edad", "comunidad_autonoma", "nivel_geografico"]
    grouped: dict[tuple, dict] = {}
    for rec in records:
        key = tuple(rec[k] for k in keys)
        row = grouped.setdefault(key, {k: rec[k] for k in keys})
        col = rec["variable"]
        value = rec["valor"]
        if col not in row or row[col] in (None, ""):
            row[col] = value
        aggregate = "subsidio de desempleo por no cotizacion suficiente"
        if rec["variable"].startswith(aggregate + " - "):
            row[aggregate] = (row.get(aggregate) or 0) + value
    preferred = [
        "total prestacion contributiva",
        "total subsidios de desempleo",
        "subsidios de desempleo de mayores",
        "subsidio de desempleo por agotamiento de la prestacion contributiva",
        "subsidio de desempleo por no cotizacion suficiente",
        "Tasa de cobertura",
    ]
    for row in grouped.values():
        ordered = {k: row.get(k) for k in keys}
        for field in preferred:
            if field in row:
                ordered[field] = row[field]
        for field in sorted(k for k in row if k not in ordered):
            ordered[field] = row[field]
        row.clear()
        row.update(ordered)
    return sorted(grouped.values(), key=lambda r: (r["año"], r["mes"], r["sexo"], r["nivel_geografico"], r["comunidad_autonoma"], r["provincia"], r["edad"]))


def slug(text: str) -> str:
    replacements = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")
    text = norm_text(text).translate(replacements).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "value"


def write_xlsx(rows: list[dict], path: Path, headers: list[str] | None = None) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "sepe_prestaciones_wide"
    headers = headers or list(rows[0].keys())
    ws.append(headers)
    for row in rows:
        ws.append([row.get(h) for h in headers])
    ws.freeze_panes = "A2"
    for col in ws.columns:
        header = str(col[0].value or "")
        ws.column_dimensions[col[0].column_letter].width = min(max(len(header) + 2, 12), 45)
    wb.save(path)


def process_paths(paths: list[Path]) -> list[dict]:
    manifest = load_manifest()
    by_name = {Path(v.get("local_path", "")).name: v.get("source_url", "") for v in manifest.get("files", {}).values()}
    records = []
    for path in paths:
        records.extend(parse_workbook(path, by_name.get(path.name)))
    export_records(records)
    return records


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Download and reshape SEPE prestaciones Excel workbooks.")
    parser.add_argument("--no-download", action="store_true", help="Process existing files in data/raw only.")
    parser.add_argument("--limit", type=int, help="Limit discovered downloads for smoke tests.")
    parser.add_argument("--from-year", type=int, help="Only include files from this year onward.")
    parser.add_argument("--to-year", type=int, help="Only include files up to this year.")
    args = parser.parse_args(argv)

    if args.no_download:
        paths = sorted(RAW_DIR.glob("*.xlsx"))
    else:
        files = discover_files()
        if args.from_year:
            files = [f for f in files if f.year >= args.from_year]
        if args.to_year:
            files = [f for f in files if f.year <= args.to_year]
        paths = download_files(files, args.limit)
    records = process_paths(paths)
    print(f"Processed {len(paths)} workbook(s), {len(records)} long records.")
    print(f"Wrote {PROCESSED_DIR / 'sepe_prestaciones_long.csv'}")
    print(f"Wrote {PROCESSED_DIR / 'sepe_prestaciones_wide.csv'}")


if __name__ == "__main__":
    main(sys.argv[1:])

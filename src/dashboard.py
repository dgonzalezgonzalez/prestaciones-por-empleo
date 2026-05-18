from __future__ import annotations

import csv
import json
from pathlib import Path


DASHBOARD_DIR = Path("data/dashboard")
DASHBOARD_PATH = DASHBOARD_DIR / "index.html"
GEO_TOPO_PATH = Path("data/geo/spain-provinces-topo.json")

MAIN_FIELDS = [
    "total prestacion contributiva",
    "total subsidios de desempleo",
    "tasa de cobertura",
]
SUBSIDY_FIELDS = [
    "subsidios de desempleo de mayores",
    "subsidio de desempleo por agotamiento de la prestacion contributiva",
    "subsidio de desempleo por no cotizacion suficiente",
    "subsidio de desempleo para emigrantes retornados",
    "subsidio de desempleo para liberados de prision",
    "subsidio de desempleo por revision de invalidez",
    "subsidio de desempleo para fijos discontinuos",
    "subsidio extraordinario por desempleo (SED)",
    "subsidio VVGS",
    "complemento de apoyo al empleo (CAE)",
]


def generate_dashboard(csv_path: Path) -> Path:
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    payload = build_dashboard_payload(csv_path)
    DASHBOARD_PATH.write_text(dashboard_html(payload), encoding="utf-8")
    return DASHBOARD_PATH


def build_dashboard_payload(csv_path: Path) -> dict:
    rows = []
    subtype_rows = []
    periods = set()
    sexes = set()
    ages = set()
    ccaa = set()
    provinces_by_ccaa: dict[str, set[str]] = {}
    latest = ""

    with csv_path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            period = f"{int(row['año']):04d}-{int(row['mes']):02d}"
            latest = max(latest, period)
            sex = row["sexo"]
            age = row["edad"]
            level = row["nivel geografico"]
            region = row["comunidad autonoma"]
            province = row["provincia"]
            pc = parse_number(row.get(MAIN_FIELDS[0]))
            sub = parse_number(row.get(MAIN_FIELDS[1]))
            cov = parse_number(row.get(MAIN_FIELDS[2]))
            if pc is not None or sub is not None or cov is not None:
                rows.append([
                    period, sex, age, level, region, province,
                    round(pc, 6) if pc is not None else None,
                    round(sub, 6) if sub is not None else None,
                    round(cov, 6) if cov is not None else None,
                ])
            subtype_values = [parse_number(row.get(field)) for field in SUBSIDY_FIELDS]
            if any(value is not None for value in subtype_values):
                subtype_rows.append([
                    period, sex, level, region, province,
                    [round(value, 6) if value is not None else None for value in subtype_values],
                ])
            periods.add(period)
            sexes.add(sex)
            ages.add(age)
            if level == "comunidad_autonoma":
                ccaa.add(region)
            elif level == "provincia":
                ccaa.add(region)
                provinces_by_ccaa.setdefault(region, set()).add(province)

    return {
        "latest": latest,
        "periods": sorted(periods),
        "sexes": sorted(sexes, key=lambda x: {"Ambos sexos": 0, "Hombres": 1, "Mujeres": 2}.get(x, 9)),
        "ages": sorted(ages, key=age_sort_key),
        "ccaa": sorted(ccaa, key=territory_sort_key),
        "provincesByCcaa": {
            key: sorted(value, key=territory_sort_key)
            for key, value in sorted(provinces_by_ccaa.items(), key=lambda item: territory_sort_key(item[0]))
        },
        "subsidyFields": SUBSIDY_FIELDS,
        "geoTopology": json.loads(GEO_TOPO_PATH.read_text(encoding="utf-8")) if GEO_TOPO_PATH.exists() else None,
        "rows": rows,
        "subtypeRows": subtype_rows,
    }


def parse_number(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        text = value.replace(".", "").replace(",", ".")
        try:
            return float(text)
        except ValueError:
            return None


def age_sort_key(value: str) -> tuple[int, str]:
    order = {
        "Todas las edades": 0,
        "16 - 19 años": 16,
        "20 - 24 años": 20,
        "25 - 29 años": 25,
        "30 - 34 años": 30,
        "35 - 39 años": 35,
        "40 - 44 años": 40,
        "45 - 49 años": 45,
        "50 - 54 años": 50,
        "55 - 59 años": 55,
        "60 y más años": 60,
    }
    return (order.get(value, 999), value)


def territory_sort_key(value: str) -> str:
    if value == "España":
        return "0"
    if value == "Todas las provincias":
        return "1"
    return value


def dashboard_html(payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Indicadores de prestaciones por desempleo</title>
  <style>
    :root {{
      --burgundy: #83082A;
      --crimson: #D00D43;
      --rose: #E397A0;
      --rose-2: #D46271;
      --text: #404040;
      --muted: #6f6f6f;
      --grid: #CCCCCC;
      --line: #e4d7db;
      --page: #f6f3f4;
      --panel: #ffffff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--page);
      color: var(--text);
      font-family: "Century Gothic", "Aptos", "Segoe UI", sans-serif;
      letter-spacing: 0;
    }}
    header {{
      background: #fff;
      border-bottom: 1px solid var(--line);
    }}
    .topbar, main, footer {{
      max-width: 1280px;
      margin: 0 auto;
      padding-left: 24px;
      padding-right: 24px;
    }}
    .topbar {{
      min-height: 62px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 24px;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 18px;
      min-width: 0;
    }}
    .logo {{
      width: 38px;
      height: 38px;
      object-fit: contain;
      display: block;
    }}
    h1 {{
      margin: 0;
      font-size: 25px;
      line-height: 1.2;
      font-weight: 700;
    }}
    .subtitle {{
      margin: 5px 0 0;
      font-size: 13px;
      color: var(--muted);
    }}
    main {{
      padding-top: 22px;
      padding-bottom: 32px;
    }}
    .tabs {{
      display: flex;
      gap: 4px;
      border-bottom: 1px solid var(--line);
      margin-bottom: 16px;
    }}
    .tab {{
      appearance: none;
      border: 0;
      background: transparent;
      color: var(--text);
      padding: 14px 22px;
      font: inherit;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      border-bottom: 4px solid transparent;
    }}
    .tab[aria-selected="true"] {{
      color: var(--burgundy);
      border-bottom-color: var(--burgundy);
    }}
    .filters {{
      display: grid;
      grid-template-columns: repeat(6, minmax(130px, 1fr));
      gap: 12px;
      margin: 16px 0 18px;
      align-items: end;
    }}
    label {{
      display: grid;
      gap: 6px;
      font-size: 12px;
      font-weight: 700;
      color: var(--text);
    }}
    select {{
      width: 100%;
      min-height: 36px;
      border: 1px solid var(--line);
      border-radius: 3px;
      background: #fff;
      color: var(--text);
      padding: 6px 9px;
      font: inherit;
      font-size: 13px;
    }}
    input[type="range"] {{
      width: 100%;
      accent-color: var(--burgundy);
    }}
    .period-control {{
      border: 1px solid var(--line);
      border-radius: 3px;
      background: #fff;
      min-height: 36px;
      padding: 5px 9px;
    }}
    .period-value {{
      color: var(--burgundy);
      font-size: 12px;
      font-weight: 700;
      text-align: right;
      margin-top: 2px;
    }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin: 0 0 16px;
    }}
    .kpi {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      border-top: 4px solid var(--burgundy);
      box-shadow: 0 2px 7px rgba(64,64,64,.14);
      padding: 16px;
      min-height: 92px;
    }}
    .kpi span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }}
    .kpi strong {{
      display: block;
      margin-top: 8px;
      color: var(--burgundy);
      font-size: 24px;
      line-height: 1;
    }}
    .grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(330px, 0.9fr);
      gap: 16px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 2px 7px rgba(64,64,64,.14);
      min-width: 0;
      overflow: hidden;
    }}
    .panel-head {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
      align-items: start;
      padding: 16px 16px 0;
    }}
    h2 {{
      margin: 0;
      font-size: 16px;
      line-height: 1.25;
      font-weight: 700;
    }}
    .desc {{
      margin: 5px 0 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }}
    .csv {{
      border: 1px solid var(--burgundy);
      background: #fff;
      color: var(--burgundy);
      min-width: 52px;
      height: 30px;
      font: inherit;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
    }}
    .chart {{
      width: 100%;
      height: 360px;
      display: block;
      overflow: visible;
      padding: 6px 12px 14px;
    }}
    .map {{
      height: 460px;
    }}
    .wide {{
      grid-column: 1 / -1;
    }}
    .source {{
      display: none;
      margin: 0;
      padding: 0 16px 14px;
      color: var(--muted);
      font-size: 11px;
    }}
    .tooltip {{
      position: fixed;
      z-index: 20;
      pointer-events: none;
      opacity: 0;
      max-width: 260px;
      background: #fff;
      border: 1px solid var(--line);
      box-shadow: 0 10px 26px rgba(64,64,64,.16);
      padding: 9px 10px;
      font-size: 12px;
      line-height: 1.35;
    }}
    footer {{
      max-width: none;
      background: #4f0018;
      padding-top: 18px;
      padding-bottom: 28px;
      color: #fff;
      font-size: 12px;
      text-align: center;
    }}
    @media (max-width: 980px) {{
      .filters {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .grid {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 640px) {{
      .topbar, main, footer {{ padding-left: 14px; padding-right: 14px; }}
      .topbar {{ align-items: start; padding-top: 16px; padding-bottom: 16px; }}
      .brand {{ align-items: start; flex-direction: column; gap: 8px; }}
      h1 {{ font-size: 21px; }}
      .tabs {{ overflow-x: auto; }}
      .tab {{ white-space: nowrap; padding-left: 12px; padding-right: 12px; }}
      .filters, .kpis {{ grid-template-columns: 1fr; }}
      .chart {{ height: 310px; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="topbar">
      <div class="brand">
        <img class="logo" src="airef-logo.png" alt="AIReF">
        <div>
          <h1>Indicadores de prestaciones por desempleo</h1>
          <p class="subtitle">Dashboard interactivo de análisis de prestaciones SEPE (2017-2026)</p>
        </div>
      </div>
    </div>
  </header>
  <main>
    <nav class="tabs" aria-label="Tipo de prestación">
      <button class="tab" data-tab="pc" aria-selected="true">Prestación contributiva</button>
      <button class="tab" data-tab="sub" aria-selected="false">Subsidios de desempleo</button>
    </nav>

    <section class="filters" aria-label="Filtros">
      <label>Sexo<select id="sex"></select></label>
      <label>Edad<select id="age"></select></label>
      <label>Territorio<select id="territoryLevel"></select></label>
      <label>Comunidad autónoma<select id="ccaa"></select></label>
      <label>Provincia<select id="province"></select></label>
      <label>Periodo
        <div class="period-control">
          <input id="period" type="range" step="1">
          <div class="period-value" id="periodLabel"></div>
        </div>
      </label>
    </section>

    <section class="kpis">
      <div class="kpi"><span>Beneficiarios selección</span><strong id="kpiBeneficiaries">--</strong></div>
      <div class="kpi"><span>Peso sobre total nacional</span><strong id="kpiShare">--</strong></div>
      <div class="kpi"><span>Tasa de cobertura</span><strong id="kpiCoverage">--</strong></div>
      <div class="kpi"><span>Última variación interanual</span><strong id="kpiYoY">--</strong></div>
    </section>

    <section class="grid">
      <article class="panel wide" id="evolutionPanel">
        <div class="panel-head">
          <div>
            <h2>Evolución de beneficiarios y tasa de cobertura</h2>
            <p class="desc">Serie mensual filtrada por sexo, edad y territorio.</p>
          </div>
          <button class="csv" data-download="evolution">CSV</button>
        </div>
        <svg id="evolution" class="chart" role="img"></svg>
        <p class="source">Fuente: AIReF a partir de SEPE.</p>
      </article>

      <article class="panel">
        <div class="panel-head">
          <div>
            <h2>Perfil por edad</h2>
            <p class="desc">Distribución de beneficiarios en el periodo seleccionado.</p>
          </div>
          <button class="csv" data-download="age">CSV</button>
        </div>
        <svg id="ageChart" class="chart" role="img"></svg>
        <p class="source">Fuente: AIReF a partir de SEPE.</p>
      </article>

      <article class="panel">
        <div class="panel-head">
          <div>
            <h2>Mapa territorial</h2>
            <p class="desc">Comunidades autónomas y provincias según disponibilidad.</p>
          </div>
          <button class="csv" data-download="map">CSV</button>
        </div>
        <svg id="map" class="chart map" role="img"></svg>
        <p class="source">Fuente: AIReF a partir de SEPE.</p>
      </article>

      <article class="panel wide" id="subtypesPanel">
        <div class="panel-head">
          <div>
            <h2>Desglose de subsidios</h2>
            <p class="desc">Tipos de subsidio para todas las edades.</p>
          </div>
          <button class="csv" data-download="subtypes">CSV</button>
        </div>
        <svg id="subtypes" class="chart map" role="img"></svg>
        <p class="source">Fuente: AIReF a partir de SEPE.</p>
      </article>

      <article class="panel wide" id="subsidyLinesPanel">
        <div class="panel-head">
          <div>
            <h2>Evolución por tipo de subsidio</h2>
            <p class="desc">Series mensuales de los principales tipos de subsidio.</p>
          </div>
          <button class="csv" data-download="subsidyLines">CSV</button>
        </div>
        <svg id="subsidyLines" class="chart" role="img"></svg>
        <p class="source">Fuente: AIReF a partir de SEPE.</p>
      </article>
    </section>
  </main>
  <footer>© Autoridad Independiente de Responsabilidad Fiscal (AIReF), AAI. Todos los derechos reservados.</footer>
  <div id="tooltip" class="tooltip"></div>

  <script>
    const db = {data};
    const state = {{ tab: "pc" }};
    const idx = {{ period: 0, sex: 1, age: 2, level: 3, ccaa: 4, province: 5, pc: 6, sub: 7, cov: 8 }};
    const tileMap = {{
      "Galicia": [0, 1], "Asturias, Principado de": [1, 0], "Cantabria": [2, 0], "País Vasco": [3, 0],
      "Navarra, Comunidad Foral de": [4, 1], "Rioja, La": [3, 1], "Aragón": [4, 2],
      "Castilla y León": [2, 2], "Madrid, Comunidad de": [3, 3], "Castilla-La Mancha": [3, 4],
      "Cataluña": [5, 2], "Comunitat Valenciana": [5, 4], "Extremadura": [1, 4],
      "Andalucía": [2, 6], "Murcia, Región de": [4, 6], "Balears, Illes": [6, 5],
      "Canarias": [0, 7], "Ceuta": [3, 7], "Melilla": [4, 7]
    }};
    const shortNames = {{
      "Asturias, Principado de": "Asturias", "Madrid, Comunidad de": "Madrid",
      "Murcia, Región de": "Murcia", "Navarra, Comunidad Foral de": "Navarra"
    }};
    const els = {{
      sex: document.getElementById("sex"), age: document.getElementById("age"),
      territoryLevel: document.getElementById("territoryLevel"), ccaa: document.getElementById("ccaa"),
      province: document.getElementById("province"), period: document.getElementById("period"),
      tip: document.getElementById("tooltip"), periodLabel: document.getElementById("periodLabel")
    }};
    const downloads = {{}};

    function option(select, value, label = value) {{
      const opt = document.createElement("option");
      opt.value = value;
      opt.textContent = label;
      select.appendChild(opt);
    }}
    function init() {{
      db.sexes.forEach(v => option(els.sex, v));
      db.ages.forEach(v => option(els.age, v));
      option(els.territoryLevel, "espana", "España");
      option(els.territoryLevel, "comunidad_autonoma", "Comunidad autónoma");
      option(els.territoryLevel, "provincia", "Provincia");
      option(els.ccaa, "España");
      db.ccaa.forEach(v => option(els.ccaa, v));
      els.period.min = 0;
      els.period.max = db.periods.length - 1;
      els.period.value = Math.max(0, db.periods.indexOf(db.latest));
      updatePeriodLabel();
      els.age.value = "Todas las edades";
      updateProvinceOptions();
      document.querySelectorAll(".tab").forEach(btn => btn.addEventListener("click", () => {{
      state.tab = btn.dataset.tab;
        document.querySelectorAll(".tab").forEach(node => node.setAttribute("aria-selected", String(node === btn)));
        render();
      }}));
      Object.values(els).forEach(el => {{
        if (el && el.tagName !== "DIV") el.addEventListener("input", () => {{
          if (el === els.period) updatePeriodLabel();
          if (el === els.period) render();
        }});
        if (el && el.tagName !== "DIV") el.addEventListener("change", () => {{
          if (el === els.ccaa || el === els.territoryLevel) updateProvinceOptions();
          if (el === els.period) updatePeriodLabel();
          render();
        }});
      }});
      document.querySelectorAll("[data-download]").forEach(btn => btn.addEventListener("click", () => downloadCsv(btn.dataset.download)));
      render();
    }}
    function updateProvinceOptions() {{
      if (els.territoryLevel.value === "espana") els.ccaa.value = "España";
      if (els.territoryLevel.value !== "espana" && els.ccaa.value === "España") els.ccaa.value = db.ccaa[0] || "España";
      els.province.innerHTML = "";
      option(els.province, "Todas las provincias");
      const region = els.ccaa.value;
      if (region && db.provincesByCcaa[region]) db.provincesByCcaa[region].forEach(v => option(els.province, v));
      if (els.territoryLevel.value === "provincia" && els.province.value === "Todas las provincias" && els.province.options.length > 1) els.province.selectedIndex = 1;
      els.ccaa.disabled = els.territoryLevel.value === "espana";
      els.province.disabled = els.territoryLevel.value !== "provincia";
    }}
    function currentPeriod() {{
      return db.periods[Math.max(0, Math.min(db.periods.length - 1, Number(els.period.value) || 0))];
    }}
    function updatePeriodLabel() {{
      if (els.periodLabel) els.periodLabel.textContent = currentPeriod();
    }}
    function selectedMetric(row) {{ return state.tab === "pc" ? row[idx.pc] : row[idx.sub]; }}
    function rowMatches(row, extra = {{}}) {{
      const level = extra.level ?? els.territoryLevel.value;
      const age = extra.age ?? els.age.value;
      const sex = extra.sex ?? els.sex.value;
      if (row[idx.sex] !== sex || row[idx.age] !== age || row[idx.level] !== level) return false;
      if (level === "espana") return row[idx.ccaa] === "España";
      if (level === "comunidad_autonoma") return row[idx.ccaa] === els.ccaa.value && row[idx.province] === "Todas las provincias";
      return row[idx.ccaa] === els.ccaa.value && row[idx.province] === els.province.value;
    }}
    function currentRows() {{
      return db.rows.filter(rowMatches).sort((a, b) => a[idx.period].localeCompare(b[idx.period]));
    }}
    function periodRows(period, level, age = "Todas las edades", sex = els.sex.value) {{
      return db.rows.filter(row => row[idx.period] === period && row[idx.level] === level && row[idx.age] === age && row[idx.sex] === sex);
    }}
    function fmtInt(value) {{ return value == null || Number.isNaN(value) ? "--" : Math.round(value).toLocaleString("es-ES"); }}
    function fmtPct(value) {{ return value == null || Number.isNaN(value) ? "--" : value.toLocaleString("es-ES", {{ maximumFractionDigits: 1 }}) + " %"; }}
    function showTip(evt, html) {{
      els.tip.innerHTML = html;
      els.tip.style.left = evt.clientX + 12 + "px";
      els.tip.style.top = evt.clientY - 10 + "px";
      els.tip.style.opacity = 1;
    }}
    function hideTip() {{ els.tip.style.opacity = 0; }}
    function clear(svg) {{ while (svg.firstChild) svg.removeChild(svg.firstChild); }}
    function node(svg, name, attrs = {{}}, text = "") {{
      const n = document.createElementNS("http://www.w3.org/2000/svg", name);
      Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v));
      if (text !== "") n.textContent = text;
      svg.appendChild(n);
      return n;
    }}
    function dims(svg) {{
      const rect = svg.getBoundingClientRect();
      const w = Math.max(320, rect.width);
      const h = Math.max(280, rect.height);
      svg.setAttribute("viewBox", `0 0 ${{w}} ${{h}}`);
      return {{ w, h, m: {{ t: 42, r: 72, b: 72, l: 86 }} }};
    }}
    function render() {{
      document.getElementById("subtypesPanel").style.display = state.tab === "sub" ? "" : "none";
      document.getElementById("subsidyLinesPanel").style.display = state.tab === "sub" ? "" : "none";
      const rows = currentRows();
      renderKpis(rows);
      renderEvolution(rows);
      renderAge();
      renderMap();
      if (state.tab === "sub") {{
        renderSubtypes();
        renderSubsidyLines();
      }}
    }}
    function renderKpis(rows) {{
      const period = currentPeriod();
      const row = rows.find(r => r[idx.period] === period) || rows[rows.length - 1];
      const value = row ? selectedMetric(row) : null;
      const national = db.rows.find(r => r[idx.period] === period && r[idx.sex] === els.sex.value && r[idx.age] === els.age.value && r[idx.level] === "espana" && r[idx.ccaa] === "España");
      const natValue = national ? selectedMetric(national) : null;
      const prev = rows.find(r => r[idx.period] === shiftYear(period, -1));
      const yoy = row && prev && selectedMetric(prev) ? (selectedMetric(row) / selectedMetric(prev) - 1) * 100 : null;
      document.getElementById("kpiBeneficiaries").textContent = fmtInt(value);
      document.getElementById("kpiShare").textContent = natValue ? fmtPct(value / natValue * 100) : "--";
      document.getElementById("kpiCoverage").textContent = row ? fmtPct(row[idx.cov]) : "--";
      document.getElementById("kpiYoY").textContent = yoy == null ? "--" : fmtPct(yoy);
    }}
    function shiftYear(period, delta) {{
      const [y, m] = period.split("-").map(Number);
      return `${{y + delta}}-${{String(m).padStart(2, "0")}}`;
    }}
    function renderEvolution(rows) {{
      const svg = document.getElementById("evolution"); clear(svg);
      const {{ w, h, m }} = dims(svg);
      const values = rows.map(r => selectedMetric(r)).filter(v => v != null);
      if (!values.length) return noData(svg, w, h);
      const maxY = Math.max(...values) * 1.12;
      const maxC = Math.max(...rows.map(r => r[idx.cov] || 0), 1) * 1.12;
      const x = (i) => m.l + i / Math.max(1, rows.length - 1) * (w - m.l - m.r);
      const y = v => h - m.b - v / maxY * (h - m.t - m.b);
      const yc = v => h - m.b - v / maxC * (h - m.t - m.b);
      grid(svg, w, h, m, 5, maxY, v => fmtInt(v));
      rightAxis(svg, w, h, m, 5, maxC, v => fmtPct(v).replace(" %", ""));
      axisLabels(svg, rows, x, h, m);
      axisTitles(svg, w, h, m, "Periodo", "Beneficiarios");
      const metricPts = rows.map((r, i) => [x(i), y(selectedMetric(r) || 0), r]);
      const covPts = rows.filter(r => r[idx.cov] != null).map(r => [x(rows.indexOf(r)), yc(r[idx.cov]), r]);
      smoothLine(svg, metricPts, "#83082A", 2.5);
      smoothLine(svg, covPts, "#404040", 1.8, "6 4");
      hoverPoints(svg, metricPts, r => `<strong>${{r[idx.period]}}</strong><br>${{state.tab === "pc" ? "Prestación contributiva" : "Subsidios"}}: ${{fmtInt(selectedMetric(r))}}`);
      hoverPoints(svg, covPts, r => `<strong>${{r[idx.period]}}</strong><br>Tasa de cobertura: ${{fmtPct(r[idx.cov])}}`, "#404040");
      node(svg, "text", {{ x: m.l, y: 18, fill: "#83082A", "font-size": 12, "font-weight": 700 }}, state.tab === "pc" ? "Prestación contributiva" : "Subsidios de desempleo");
      node(svg, "text", {{ x: m.l + 180, y: 18, fill: "#404040", "font-size": 12, "font-weight": 700 }}, "Tasa de cobertura");
      downloads.evolution = [["Periodo","Beneficiarios","Tasa de cobertura"], ...rows.map(r => [r[idx.period], selectedMetric(r), r[idx.cov]])];
    }}
    function renderMix() {{
      const svg = document.getElementById("mix"); clear(svg);
      const {{ w, h, m }} = dims(svg);
      const rows = currentRows();
      const data = rows.filter(r => r[idx.pc] != null || r[idx.sub] != null);
      if (!data.length) return noData(svg, w, h);
      const maxY = Math.max(...data.map(r => (r[idx.pc] || 0) + (r[idx.sub] || 0))) * 1.12;
      const x = i => m.l + i / Math.max(1, data.length - 1) * (w - m.l - m.r);
      const y = v => h - m.b - v / maxY * (h - m.t - m.b);
      grid(svg, w, h, m, 5);
      axisLabels(svg, data, x, h, m);
      area(svg, data.map((r, i) => [x(i), y(r[idx.pc] || 0), y((r[idx.pc] || 0) + (r[idx.sub] || 0))]), h - m.b);
      node(svg, "rect", {{ x: m.l, y: 10, width: 12, height: 12, fill: "#83082A" }});
      node(svg, "text", {{ x: m.l + 18, y: 20, fill: "#404040", "font-size": 12 }}, "Prestación contributiva");
      node(svg, "rect", {{ x: m.l + 180, y: 10, width: 12, height: 12, fill: "#E397A0" }});
      node(svg, "text", {{ x: m.l + 198, y: 20, fill: "#404040", "font-size": 12 }}, "Subsidios");
      downloads.mix = [["Periodo","Prestación contributiva","Subsidios"], ...data.map(r => [r[idx.period], r[idx.pc], r[idx.sub]])];
    }}
    function renderAge() {{
      const svg = document.getElementById("ageChart"); clear(svg);
      const {{ w, h, m }} = dims(svg);
      m.b = 104;
      const rows = db.rows.filter(r => r[idx.period] === currentPeriod() && r[idx.sex] === els.sex.value && r[idx.level] === els.territoryLevel.value && r[idx.age] !== "Todas las edades");
      const scoped = rows.filter(r => els.territoryLevel.value === "espana" ? r[idx.ccaa] === "España" : els.territoryLevel.value === "comunidad_autonoma" ? r[idx.ccaa] === els.ccaa.value : r[idx.ccaa] === els.ccaa.value && r[idx.province] === els.province.value);
      const data = db.ages.filter(a => a !== "Todas las edades").map(age => scoped.find(r => r[idx.age] === age)).filter(Boolean);
      if (!data.length) return noData(svg, w, h);
      bars(svg, data.map(r => [r[idx.age], selectedMetric(r)]), w, h, m, "#83082A");
      axisTitles(svg, w, h, m, "Edad", "Beneficiarios");
      downloads.age = [["Edad","Beneficiarios"], ...data.map(r => [r[idx.age], selectedMetric(r)])];
    }}
    function renderMap() {{
      const svg = document.getElementById("map"); clear(svg);
      const {{ w, h }} = dims(svg);
      const period = currentPeriod();
      const level = els.territoryLevel.value === "provincia" ? "provincia" : "comunidad_autonoma";
      const rows = periodRows(period, level).filter(r => level === "provincia" ? r[idx.ccaa] === els.ccaa.value : r[idx.province] === "Todas las provincias");
      if (!rows.length) return noData(svg, w, h);
      if (!db.geoTopology) return noData(svg, w, h);
      const vals = rows.map(r => selectedMetric(r) || 0);
      const min = Math.min(...vals), max = Math.max(...vals);
      const rowByName = new Map(rows.map(r => [normName(level === "provincia" ? r[idx.province] : r[idx.ccaa]), r]));
      const features = topoFeatures(db.geoTopology, level === "provincia" ? "provinces" : "autonomous_regions")
        .filter(f => rowByName.has(normName(f.properties.name)));
      const projected = projectFeatures(features, w, h);
      if (!projected.length) return noData(svg, w, h);
      projected.forEach(f => {{
        const r = rowByName.get(normName(f.properties.name));
        const value = selectedMetric(r) || 0;
        const path = node(svg, "path", {{ d: f.path, fill: ramp(value, min, max), stroke: "#fff", "stroke-width": 1.2 }});
        path.addEventListener("mousemove", e => showTip(e, `<strong>${{level === "provincia" ? r[idx.province] : r[idx.ccaa]}}</strong><br>${{fmtInt(value)}} beneficiarios<br>Cobertura: ${{fmtPct(r[idx.cov])}}`));
        path.addEventListener("mouseleave", hideTip);
      }});
      node(svg, "text", {{ x: 20, y: h - 14, fill: "#404040", "font-size": 11, "font-style": "italic" }}, level === "provincia" ? "Mapa provincial" : "Mapa por comunidad autónoma");
      downloads.map = [[level === "provincia" ? "Provincia" : "Comunidad autónoma","Beneficiarios","Tasa de cobertura"], ...rows.map(r => [level === "provincia" ? r[idx.province] : r[idx.ccaa], selectedMetric(r), r[idx.cov]])];
    }}
    function renderSubtypes() {{
      const svg = document.getElementById("subtypes"); clear(svg);
      const {{ w, h, m }} = dims(svg);
      const row = db.subtypeRows.find(r => r[0] === currentPeriod() && r[1] === els.sex.value && r[2] === els.territoryLevel.value && (els.territoryLevel.value === "espana" ? r[3] === "España" : els.territoryLevel.value === "comunidad_autonoma" ? r[3] === els.ccaa.value && r[4] === "Todas las provincias" : r[3] === els.ccaa.value && r[4] === els.province.value));
      if (!row) return noData(svg, w, h);
      const data = db.subsidyFields.map((name, i) => [cleanSubsidy(name), row[5][i] || 0]).filter(d => d[1] > 0).sort((a, b) => b[1] - a[1]).slice(0, 10);
      const subM = {{ t: 24, r: 52, b: 54, l: 310 }};
      bars(svg, data, w, h, subM, "#83082A", true);
      xAxisTitle(svg, w, h, subM, "Beneficiarios");
      downloads.subtypes = [["Tipo de subsidio","Beneficiarios"], ...data];
    }}
    function renderSubsidyLines() {{
      const svg = document.getElementById("subsidyLines"); clear(svg);
      const {{ w, h, m }} = dims(svg);
      m.t = 96;
      const seriesRows = db.subtypeRows
        .filter(r => r[1] === els.sex.value && r[2] === els.territoryLevel.value && (
          els.territoryLevel.value === "espana" ? r[3] === "España" :
          els.territoryLevel.value === "comunidad_autonoma" ? r[3] === els.ccaa.value && r[4] === "Todas las provincias" :
          r[3] === els.ccaa.value && r[4] === els.province.value
        ))
        .sort((a, b) => a[0].localeCompare(b[0]));
      if (!seriesRows.length) return noData(svg, w, h);
      const latest = seriesRows[seriesRows.length - 1];
      const top = db.subsidyFields
        .map((name, i) => [name, latest[5][i] || 0, i])
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5);
      const maxY = Math.max(...seriesRows.flatMap(r => top.map(t => r[5][t[2]] || 0)), 1) * 1.12;
      const x = i => m.l + i / Math.max(1, seriesRows.length - 1) * (w - m.l - m.r);
      const y = v => h - m.b - v / maxY * (h - m.t - m.b);
      const colors = ["#83082A", "#D00D43", "#D46271", "#E397A0", "#404040"];
      grid(svg, w, h, m, 5, maxY, v => fmtInt(v));
      axisLabels(svg, seriesRows.map(r => ({{ [idx.period]: r[0] }})), x, h, m);
      axisTitles(svg, w, h, m, "Periodo", "Beneficiarios");
      top.forEach((t, si) => {{
        const pts = seriesRows.map((r, i) => [x(i), y(r[5][t[2]] || 0), r]);
        smoothLine(svg, pts, colors[si], 2.2);
        hoverPoints(svg, pts, r => `<strong>${{r[0]}}</strong><br>${{cleanSubsidy(t[0])}}: ${{fmtInt(r[5][t[2]] || 0)}}`, colors[si]);
        const lx = m.l + (si % 2) * 360;
        const ly = 18 + Math.floor(si / 2) * 18;
        node(svg, "rect", {{ x: lx, y: ly - 9, width: 10, height: 10, fill: colors[si] }});
        node(svg, "text", {{ x: lx + 16, y: ly, fill: "#404040", "font-size": 11 }}, cleanSubsidy(t[0]));
      }});
      downloads.subsidyLines = [["Periodo", ...top.map(t => cleanSubsidy(t[0]))], ...seriesRows.map(r => [r[0], ...top.map(t => r[5][t[2]] || 0)])];
    }}
    function grid(svg, w, h, m, count, maxValue = null, formatter = v => v) {{
      for (let i = 0; i <= count; i++) {{
        const y = m.t + i / count * (h - m.t - m.b);
        node(svg, "line", {{ x1: m.l, y1: y, x2: w - m.r, y2: y, stroke: "#CCCCCC" }});
        if (maxValue != null) node(svg, "text", {{ x: m.l - 8, y: y + 4, "text-anchor": "end", fill: "#404040", "font-size": 10 }}, formatter(maxValue * (1 - i / count)));
      }}
    }}
    function axisTitles(svg, w, h, m, xLabel, yLabel) {{
      node(svg, "text", {{ x: (m.l + w - m.r) / 2, y: h - 8, "text-anchor": "middle", fill: "#404040", "font-size": 11, "font-style": "italic" }}, xLabel);
      node(svg, "text", {{ x: 20, y: (m.t + h - m.b) / 2, "text-anchor": "middle", fill: "#404040", "font-size": 11, transform: `rotate(-90 20 ${{(m.t + h - m.b) / 2}})` }}, yLabel);
    }}
    function xAxisTitle(svg, w, h, m, xLabel) {{
      node(svg, "text", {{ x: (m.l + w - m.r) / 2, y: h - 8, "text-anchor": "middle", fill: "#404040", "font-size": 11, "font-style": "italic" }}, xLabel);
    }}
    function rightAxis(svg, w, h, m, count, maxValue, formatter = v => v) {{
      for (let i = 0; i <= count; i++) {{
        const y = m.t + i / count * (h - m.t - m.b);
        node(svg, "text", {{ x: w - m.r + 10, y: y + 4, fill: "#404040", "font-size": 10 }}, formatter(maxValue * (1 - i / count)));
      }}
      node(svg, "text", {{ x: w - 16, y: (m.t + h - m.b) / 2, "text-anchor": "middle", fill: "#404040", "font-size": 11, transform: `rotate(90 ${{w - 16}} ${{(m.t + h - m.b) / 2}})` }}, "Tasa de cobertura");
    }}
    function axisLabels(svg, rows, x, h, m) {{
      const seen = new Set();
      rows.forEach((r, i) => {{
        const year = r[idx.period].slice(0, 4);
        if (!seen.has(year) && r[idx.period].endsWith("-01")) {{
          seen.add(year);
          node(svg, "text", {{ x: x(i), y: h - 18, "text-anchor": "middle", fill: "#404040", "font-size": 11 }}, year);
        }}
      }});
    }}
    function line(svg, points, color, width, dash = "") {{
      const d = points.map((p, i) => `${{i ? "L" : "M"}}${{p[0]}},${{p[1]}}`).join(" ");
      node(svg, "path", {{ d, fill: "none", stroke: color, "stroke-width": width, "stroke-dasharray": dash }});
    }}
    function smoothLine(svg, points, color, width, dash = "") {{
      if (!points.length) return;
      if (points.length < 3) return line(svg, points, color, width, dash);
      let d = `M${{points[0][0]}},${{points[0][1]}}`;
      for (let i = 0; i < points.length - 1; i++) {{
        const p0 = points[Math.max(0, i - 1)];
        const p1 = points[i];
        const p2 = points[i + 1];
        const p3 = points[Math.min(points.length - 1, i + 2)];
        const c1x = p1[0] + (p2[0] - p0[0]) / 6;
        const c1y = p1[1] + (p2[1] - p0[1]) / 6;
        const c2x = p2[0] - (p3[0] - p1[0]) / 6;
        const c2y = p2[1] - (p3[1] - p1[1]) / 6;
        d += ` C${{c1x}},${{c1y}} ${{c2x}},${{c2y}} ${{p2[0]}},${{p2[1]}}`;
      }}
      node(svg, "path", {{ d, fill: "none", stroke: color, "stroke-width": width, "stroke-dasharray": dash, "stroke-linecap": "round", "stroke-linejoin": "round" }});
    }}
    function hoverPoints(svg, points, html, color = "#83082A") {{
      points.forEach(p => {{
        const hit = node(svg, "circle", {{ cx: p[0], cy: p[1], r: 7, fill: "transparent", stroke: "transparent" }});
        hit.addEventListener("mousemove", e => showTip(e, html(p[2])));
        hit.addEventListener("mouseleave", hideTip);
        node(svg, "circle", {{ cx: p[0], cy: p[1], r: 3, fill: color, stroke: "#fff", "stroke-width": 1.5 }});
      }});
    }}
    function area(svg, pts, base) {{
      const top = pts.map(p => `${{p[0]}},${{p[2]}}`).join(" ");
      const mid = pts.map(p => `${{p[0]}},${{p[1]}}`).reverse().join(" ");
      const bottom = pts.map(p => `${{p[0]}},${{p[1]}}`).join(" ");
      const floor = pts.map(p => `${{p[0]}},${{base}}`).reverse().join(" ");
      node(svg, "polygon", {{ points: `${{top}} ${{mid}}`, fill: "#E397A0", opacity: .9 }});
      node(svg, "polygon", {{ points: `${{bottom}} ${{floor}}`, fill: "#83082A", opacity: .95 }});
    }}
    function bars(svg, data, w, h, m, color, horizontal = false) {{
      const max = Math.max(...data.map(d => d[1] || 0), 1);
      if (horizontal) {{
        const step = (h - m.t - m.b) / data.length;
        data.forEach((d, i) => {{
          const y = m.t + i * step + 3;
          const bw = (w - m.l - m.r) * (d[1] || 0) / max;
          node(svg, "text", {{ x: m.l - 8, y: y + step * .55, "text-anchor": "end", fill: "#404040", "font-size": 11 }}, d[0]);
          const rect = node(svg, "rect", {{ x: m.l, y, width: bw, height: Math.max(4, step * .58), fill: color }});
          rect.addEventListener("mousemove", e => showTip(e, `<strong>${{d[0]}}</strong><br>${{fmtInt(d[1])}}`));
          rect.addEventListener("mouseleave", hideTip);
        }});
        return;
      }}
      const band = (w - m.l - m.r) / data.length;
      data.forEach((d, i) => {{
        const bh = (h - m.t - m.b) * (d[1] || 0) / max;
        const x = m.l + i * band + band * .2;
        const y = h - m.b - bh;
        const rect = node(svg, "rect", {{ x, y, width: band * .6, height: bh, fill: color }});
        rect.addEventListener("mousemove", e => showTip(e, `<strong>${{d[0]}}</strong><br>${{fmtInt(d[1])}}`));
        rect.addEventListener("mouseleave", hideTip);
        const labelY = h - m.b + 48;
        node(svg, "text", {{ x: x + band * .3, y: labelY, "text-anchor": "end", fill: "#404040", "font-size": 10, transform: `rotate(-36 ${{x + band * .3}} ${{labelY}})` }}, d[0]);
      }});
    }}
    function normName(value) {{
      const aliases = {{
        "alacant alicante": "alicante alacant",
        "alicante alacant": "alicante alacant",
        "castello castellon": "castellon castello",
        "castellon castello": "castellon castello",
        "valencia valencia": "valencia valencia",
        "valencia valencia": "valencia valencia",
        "a coruna": "coruna a",
        "la coruna": "coruna a",
        "coruna a": "coruna a",
        "illes balears": "balears illes",
        "balears illes": "balears illes",
        "las palmas": "palmas las",
        "palmas las": "palmas las",
        "comunidad de madrid": "madrid comunidad de",
        "madrid comunidad de": "madrid comunidad de",
        "region de murcia": "murcia region de",
        "murcia region de": "murcia region de",
        "comunidad foral de navarra": "navarra comunidad foral de",
        "navarra comunidad foral de": "navarra comunidad foral de",
        "principado de asturias": "asturias principado de",
        "asturias principado de": "asturias principado de",
        "la rioja": "rioja la",
        "rioja la": "rioja la",
        "cataluna catalunya": "cataluna",
        "cataluna": "cataluna",
        "pais vasco euskadi": "pais vasco",
        "pais vasco": "pais vasco",
        "ciudad autonoma de ceuta": "ceuta",
        "ciudad autonoma de melilla": "melilla",
        "comunitat valenciana": "comunitat valenciana"
      }};
      const key = String(value || "")
        .normalize("NFD").replace(/[\\u0300-\\u036f]/g, "")
        .replace(/[\\/]/g, " ")
        .replace(/[^a-zA-Z0-9]+/g, " ")
        .trim().toLowerCase();
      return aliases[key] || key;
    }}
    function topoFeatures(topology, objectName) {{
      const transform = topology.transform;
      const arcs = topology.arcs.map(arc => {{
        let x = 0, y = 0;
        return arc.map(p => {{
          x += p[0]; y += p[1];
          return [x * transform.scale[0] + transform.translate[0], y * transform.scale[1] + transform.translate[1]];
        }});
      }});
      function arcById(id) {{
        if (id >= 0) return arcs[id];
        return [...arcs[-id - 1]].reverse();
      }}
      function ringPath(ring) {{
        return ring.flatMap((arcId, i) => {{
          const pts = arcById(arcId);
          return i ? pts.slice(1) : pts;
        }});
      }}
      function polygonCoords(poly) {{
        return poly.map(ringPath);
      }}
      return topology.objects[objectName].geometries
        .filter(g => !/gibraltar/i.test(g.properties?.name || ""))
        .map(g => ({{
          properties: g.properties || {{}},
          coordinates: g.type === "Polygon" ? [polygonCoords(g.arcs)] : g.arcs.map(polygonCoords)
        }}));
    }}
    function projectFeatures(features, w, h) {{
      const all = [];
      features.forEach(f => collectPoints(f.coordinates, all));
      if (!all.length) return [];
      const minLon = Math.min(...all.map(p => p[0])), maxLon = Math.max(...all.map(p => p[0]));
      const minLat = Math.min(...all.map(p => p[1])), maxLat = Math.max(...all.map(p => p[1]));
      const pad = 18;
      const sx = (w - pad * 2) / (maxLon - minLon);
      const sy = (h - pad * 2) / (maxLat - minLat);
      const s = Math.min(sx, sy);
      const ox = (w - (maxLon - minLon) * s) / 2;
      const oy = (h - (maxLat - minLat) * s) / 2;
      const proj = p => [ox + (p[0] - minLon) * s, oy + (maxLat - p[1]) * s];
      return features.map(f => {{
        const parts = f.coordinates.map(poly => poly.map(ring => ring.map(proj)));
        const d = parts.map(poly => poly.map(ring => ring.map((p, i) => `${{i ? "L" : "M"}}${{p[0]}},${{p[1]}}`).join(" ") + "Z").join(" ")).join(" ");
        return {{ properties: f.properties, path: d }};
      }});
    }}
    function collectPoints(value, out) {{
      if (Array.isArray(value) && typeof value[0] === "number" && typeof value[1] === "number") {{
        out.push(value);
        return;
      }}
      if (Array.isArray(value)) value.forEach(child => collectPoints(child, out));
    }}
    function ramp(value, min, max) {{
      const t = max === min ? .6 : Math.max(0, Math.min(1, (value - min) / (max - min)));
      const a = [246, 222, 226], b = [131, 8, 42];
      const rgb = a.map((v, i) => Math.round(v + (b[i] - v) * t));
      return `rgb(${{rgb[0]}},${{rgb[1]}},${{rgb[2]}})`;
    }}
    function abbr(name) {{
      const map = {{"Andalucía":"AND","Aragón":"ARA","Asturias, Principado de":"AST","Balears, Illes":"BAL","Canarias":"CAN","Cantabria":"CNT","Castilla y León":"CYL","Castilla-La Mancha":"CLM","Cataluña":"CAT","Comunitat Valenciana":"VAL","Extremadura":"EXT","Galicia":"GAL","Madrid, Comunidad de":"MAD","Murcia, Región de":"MUR","Navarra, Comunidad Foral de":"NAV","País Vasco":"PVA","Rioja, La":"RIO","Ceuta":"CEU","Melilla":"MEL"}};
      return map[name] || name.slice(0,3).toUpperCase();
    }}
    function cleanSubsidy(name) {{
      const labels = {{
        "subsidios de desempleo de mayores": "Mayores",
        "subsidio de desempleo por agotamiento de la prestacion contributiva": "Agotamiento prestación contributiva",
        "subsidio de desempleo por no cotizacion suficiente": "Cotización insuficiente",
        "subsidio de desempleo para emigrantes retornados": "Emigrantes retornados",
        "subsidio de desempleo para liberados de prision": "Liberados prisión",
        "subsidio de desempleo por revision de invalidez": "Revisión invalidez",
        "subsidio de desempleo para fijos discontinuos": "Fijos discontinuos",
        "subsidio extraordinario por desempleo (SED)": "SED",
        "subsidio VVGS": "VVGS",
        "complemento de apoyo al empleo (CAE)": "CAE"
      }};
      return labels[name] || name.replace("subsidio de desempleo ", "").replace("subsidios de desempleo ", "").replace("por ", "").replace("para ", "");
    }}
    function noData(svg, w, h) {{
      node(svg, "text", {{ x: w / 2, y: h / 2, "text-anchor": "middle", fill: "#6f6f6f", "font-size": 13 }}, "Sin datos para la selección");
    }}
    function downloadCsv(key) {{
      const rows = downloads[key] || [];
      if (!rows.length) return;
      const csv = rows.map(r => r.map(v => `"${{String(v ?? "").replaceAll('"', '""')}}"`).join(";")).join("\\n");
      const blob = new Blob([csv], {{ type: "text/csv;charset=utf-8" }});
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `sepe_${{key}}.csv`;
      a.click();
      URL.revokeObjectURL(a.href);
    }}
    init();
  </script>
</body>
</html>
"""

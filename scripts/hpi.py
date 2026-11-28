"""Pull California Healthy Places Index (HPI) data from the HPI API (Public Health Alliance of Southern California).

Reads the API key from the HPI_API_KEY environment variable (a GitHub secret). The key is never written to a file
or printed. Used with the Alliance's written permission to display HPI values on the dashboard.

Writes:
  data/out/hpi_catalog.json   indicator list with titles, sources, units, and years (from the public API documentation page)
  data/out/hpi_counties.json  every HPI indicator for all California counties and the state, latest year
  data/out/hpi_tracts.json    HPI score and domains for the census tracts in the dashboard counties (2020 tracts)
  data/out/hpi_probe.json     the shape of each API response (fields and a sample row), for checking the pull
Then shapes them for the dashboard (shape(), which also runs alone: python3 scripts/hpi.py shape):
  data/out/hpi_page.json      county and state values for the Community Conditions page
  data/out/hpiCardio.json, hpiEarly.json, hpiYouth.json, hpiHousing.json   topic page measures (standard format)
  data/out/hpi_geo/<fips>.json  census tract map for each dashboard county: 2020 tract boundaries from the Census Bureau
                                (cartographic boundary file, 1:500,000) joined to HPI tract percentiles by GEOID
"""
import os, sys, json, re, time, io, math, zipfile
import requests

API = "https://api.healthyplacesindex.org"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "out")
COUNTIES = {
    "Butte": "06007", "Colusa": "06011", "Del Norte": "06015", "Glenn": "06021", "Humboldt": "06023",
    "Lake": "06033", "Mendocino": "06045", "Shasta": "06089", "Tehama": "06103", "Trinity": "06105",
    "Siskiyou": "06093", "Los Angeles": "06037", "San Bernardino": "06071", "Sonoma": "06097",
    "Marin": "06041", "Sutter": "06101", "Napa": "06055", "Alameda": "06001",
}
TRACT_VARS = ["hpiscore", "economic", "education", "transportation", "social", "neighborhood", "housing",
              "clean_enviro", "healthcareaccess"]
KEY = os.environ.get("HPI_API_KEY", "").strip()


def catalog():
    html = requests.get(API + "/documentation", timeout=60).text
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    props = json.loads(m.group(1))["props"]["pageProps"]
    keep = ["varname", "title", "source", "unit", "url", "plaindefinition", "technicaldefinition", "dates", "datesDisplay", "year", "geographies"]
    return [{k: i.get(k) for k in keep} for i in props["indicators"]["hpi"]]


def get(indicator, geography, year, fmt="json"):
    """One API call. Errors name the indicator and status only, never the request URL (it carries the key)."""
    params = {"geography": geography, "year": year, "indicator": indicator, "format": fmt, "key": KEY}
    for attempt in range(3):
        try:
            r = requests.get(API + "/api/hpi", params=params, timeout=180)
        except requests.RequestException as e:
            err = type(e).__name__
        else:
            if r.status_code == 200:
                return r.json() if fmt in ("json", "geojson") else r.text
            err = f"HTTP {r.status_code}: {r.text[:200]}"
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"{indicator} / {geography} / {year}: {err}")


def rows_of(payload):
    """The API returns either a list of rows or an object holding one; find the list."""
    if isinstance(payload, list): return payload
    if isinstance(payload, dict):
        for k in ("data", "rows", "results", "features"):
            if isinstance(payload.get(k), list): return payload[k]
        lists = [v for v in payload.values() if isinstance(v, list)]
        if lists: return max(lists, key=len)
    return []


def geoid_field(row):
    props = row.get("properties", row) if isinstance(row, dict) else {}
    for k, v in props.items():
        if re.search(r"geoid|fips|tract", k, re.I) and re.fullmatch(r"0?6\d{3,9}", str(v)): return k
    return None


def in_counties(geoid):
    g = str(geoid).zfill(11)
    return g[:5] in COUNTIES.values()


def main():
    if not KEY: sys.exit("HPI_API_KEY is not set.")
    cat = catalog()
    json.dump(cat, open(os.path.join(OUT, "hpi_catalog.json"), "w"), indent=1)
    probe, counties, tracts = {}, {}, {}
    for ind in cat:
        var, year = ind["varname"], max(ind["dates"])
        entry = {"title": ind["title"], "year": year, "yearDisplay": (ind.get("datesDisplay") or [str(year)])[-1]}
        for geo in ("counties", "state"):
            try:
                rows = rows_of(get(var, geo, year))
                entry[geo] = rows
                probe[f"{var}/{geo}"] = {"n": len(rows), "fields": list(rows[0].keys()) if rows else [], "sample": rows[:2]}
            except Exception as e:
                probe[f"{var}/{geo}"] = {"error": str(e)}
            time.sleep(0.5)
        counties[var] = entry
        if var in TRACT_VARS:
            try:
                rows = rows_of(get(var, "tracts", year))
                f = geoid_field(rows[0]) if rows else None
                kept = [r for r in rows if f and in_counties(r[f])] if f else rows
                tracts[var] = {"year": year, "geoidField": f, "rows": kept}
                probe[f"{var}/tracts"] = {"n": len(rows), "kept": len(kept), "geoidField": f, "fields": list(rows[0].keys()) if rows else [], "sample": rows[:2]}
            except Exception as e:
                probe[f"{var}/tracts"] = {"error": str(e)}
            time.sleep(0.5)
    # Shape of the tract GeoJSON, for the map (geometry is saved in a later step once its size is known).
    try:
        gj = get("hpiscore", "tracts", max(next(i for i in cat if i["varname"] == "hpiscore")["dates"]), "geojson")
        feats = rows_of(gj)
        f = geoid_field(feats[0]) if feats else None
        kept = [x for x in feats if f and in_counties(x["properties"][f])]
        probe["hpiscore/tracts/geojson"] = {"n": len(feats), "kept": len(kept), "geoidField": f,
                                            "bytesKept": len(json.dumps(kept)), "properties": list(feats[0].get("properties", {}).keys()) if feats else [],
                                            "geometryType": feats[0].get("geometry", {}).get("type") if feats else None}
    except Exception as e:
        probe["hpiscore/tracts/geojson"] = {"error": str(e)}
    json.dump(counties, open(os.path.join(OUT, "hpi_counties.json"), "w"))
    json.dump(tracts, open(os.path.join(OUT, "hpi_tracts.json"), "w"))
    probe["_pulled"] = time.strftime("%Y-%m-%d", time.gmtime())
    json.dump(probe, open(os.path.join(OUT, "hpi_probe.json"), "w"), indent=1)
    errors = [k for k, v in probe.items() if isinstance(v, dict) and "error" in v]
    print(f"Indicators: {len(cat)}. Calls with errors: {len(errors)}")
    for k in errors: print("  ", k, probe[k]["error"])
    if len(errors) > len(probe) // 2: sys.exit(1)
    shape()
    tract_maps()


# ---------------------------------------------------------------------------------------------------------------
# Shaping for the dashboard. Values are shown as HPI publishes them: shares become percents (multiplied by 100 and
# rounded to one decimal), and percentiles become whole numbers from 0 to 100. Nothing else is calculated.

DOMAINS = [  # HPI policy action areas and the indicators in each (HPI 3.0)
    ("economic", "Economic", ["abovepoverty", "employed", "percapitaincome"]),
    ("education", "Education", ["bachelorsed", "inhighschool", "inpreschool"]),
    ("transportation", "Transportation", ["automobile", "commute"]),
    ("social", "Social", ["censusresponse", "voting"]),
    ("neighborhood", "Neighborhood", ["parkaccess", "retail", "treecanopy"]),
    ("housing", "Housing", ["homeownership", "houserepair", "ownsevere", "rentsevere", "uncrowded"]),
    ("clean_enviro", "Clean Environment", ["dieselpm", "h20contam", "ozone", "pm25"]),
    ("healthcareaccess", "Healthcare Access", ["insured"]),
]
# Topic page measures: only HPI indicators with no counterpart already on the dashboard from another source.
TOPIC_SETS = {
    "hpiCardio": ["commute", "treecanopy", "ozone", "dieselpm"],
    "hpiEarly": ["inpreschool"],
    "hpiYouth": ["inhighschool"],
    "hpiHousing": ["houserepair", "uncrowded", "homeownership", "rentsevere"],
}
LOWER_IS_HEALTHIER = {"dieselpm", "h20contam", "ozone", "pm25", "ownsevere", "rentsevere"}
NAME_OF = {v: k for k, v in COUNTIES.items()}
LABELS = {  # plain labels for topic page cards, in the dashboard's wording
    "commute": "Workers ages 16 and older who commute by transit, walking, or cycling",
    "treecanopy": "Land covered by tree canopy, weighted by the number of people per acre",
    "ozone": "Ozone on summer days, parts per million (average of the 8 most polluted hours)",
    "dieselpm": "Diesel particulate matter emissions, tons per year",
    "inpreschool": "Children ages 3 and 4 enrolled in school",
    "inhighschool": "Youth ages 15 to 17 enrolled in school",
    "houserepair": "Households with basic kitchen facilities and plumbing",
    "uncrowded": "Households that are not crowded",
    "homeownership": "People who own their home",
    "rentsevere": "Renter households that are low-income and spend more than 50 percent of income on housing",
}
SOURCES = {  # HPI's source names with acronyms spelled out
    "CES 4.0": "CalEnviroScreen 4.0 (CES 4.0)",
    "American Community Survey": "American Community Survey (ACS)",
    "HUD CHAS": "U.S. Department of Housing and Urban Development (HUD) Comprehensive Housing Affordability Strategy (CHAS)",
    "HCI/National Land Cover Database": "Healthy Communities Indicators (HCI) and National Land Cover Database",
    "US EPA Smart Location Database": "U.S. Environmental Protection Agency (EPA) Smart Location Database",
    "UC Berkeley Statewide Database": "UC Berkeley Statewide Database",
    "2020 Decennial Census": "2020 Decennial Census",
    "GreenInfo Network": "GreenInfo Network",
    "Public Health Alliance": "Public Health Alliance of Southern California",
}
CITE = ("California Healthy Places Index (HPI) 3.0, Public Health Alliance of Southern California, "
        "https://www.healthyplacesindex.org")


def _num(v, unit):
    if v is None: return None
    if unit == "%": return round(v * 100, 1)
    if unit == "$": return int(round(v))
    return float(f"{v:.4g}")


def _pct(p):
    return None if p is None else int(round(p * 100))


def _clean(s):
    return (s or "").replace("\u2013", "-").replace("\u2014", ", ").strip()


def shape():
    cat = {i["varname"]: i for i in json.load(open(os.path.join(OUT, "hpi_catalog.json")))}
    raw = json.load(open(os.path.join(OUT, "hpi_counties.json")))
    pr = json.load(open(os.path.join(OUT, "hpi_probe.json")))
    t = time.strptime(pr["_pulled"], "%Y-%m-%d") if "_pulled" in pr else time.gmtime(os.path.getmtime(os.path.join(OUT, "hpi_counties.json")))
    pulled = time.strftime("%B ", t) + str(t.tm_mday) + time.strftime(", %Y", t)
    ind = {}
    for var, e in raw.items():
        unit = (cat[var].get("unit") or "").strip()
        rows = {r["geoid"]: r for r in e.get("counties", [])}
        st = (e.get("state") or [{}])[0]
        ind[var] = {
            "title": cat[var]["title"], "unit": unit, "year": str(e.get("yearDisplay") or e.get("year")).replace(" - ", " to "),
            "def": _clean(cat[var].get("plaindefinition")), "src": SOURCES.get(_clean(cat[var].get("source")), _clean(cat[var].get("source"))), "url": cat[var].get("url") or "",
            "lower": var in LOWER_IS_HEALTHIER, "n": len(rows),
            "v": {NAME_OF[g]: _num(rows[g]["value"], unit) for g in COUNTIES.values() if g in rows},
            "p": {NAME_OF[g]: _pct(rows[g]["percentile"]) for g in COUNTIES.values() if g in rows},
            "ca": _num(st.get("value"), unit),
        }
    page = {"cite": CITE, "pulled": pulled, "domains": [{"id": d, "label": l, "ind": v} for d, l, v in DOMAINS], "ind": ind}
    json.dump(page, open(os.path.join(OUT, "hpi_page.json"), "w"), separators=(",", ":"))
    for key, vars_ in TOPIC_SETS.items():
        measures = []
        for var in vars_:
            x, e = ind[var], raw[var]
            unit = {"%": "percent", "$": "dollars"}.get(x["unit"], x["unit"] or "index")
            label = LABELS.get(var, x["title"])
            measures.append({
                "id": "hpi_" + var, "label": label, "unit": unit, "period": "HPI 3.0, " + x["src"] + " " + x["year"],
                "values": {c: x["v"].get(c) for c in COUNTIES}, "california": x["ca"], "california_source": "published",
                "higher_is_worse": x["lower"],
                "note": (x["def"].rstrip(".") + ". Published by the Public Health Alliance of Southern California in the California Healthy Places Index (HPI) 3.0"
                         + (", using data from the " + x["src"] if x["src"] else "") + ". The California value is the statewide value HPI publishes for the same indicator."),
                "source_url": "https://map.healthyplacesindex.org/",
                "all_ca_counties": {r["name"]: _num(r["value"], x["unit"]) for r in e.get("counties", []) if r.get("value") is not None},
                "hpi_percentile": x["p"],
            })
        json.dump({"key": key, "measures": measures, "geo_note": "County values published by HPI."}, open(os.path.join(OUT, key + ".json"), "w"))
    print("Shaped HPI page data and", len(TOPIC_SETS), "topic files.")


# ---------------------------------------------------------------------------------------------------------------
# Tract maps. Boundaries: US Census Bureau 2020 cartographic boundary file for California census tracts (public domain).
TRACT_SHP = "https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_06_tract_500k.zip"
MAP_W = 1000


def _path(rings, proj):
    """SVG path with relative moves on a whole-number grid; drops points that land on the same grid cell."""
    out = []
    for ring in rings:
        pts = []
        for lon, lat in ring:
            x, y = proj(lon, lat)
            if not pts or (x, y) != pts[-1]: pts.append((x, y))
        if len(pts) < 3: continue
        s = f"M{pts[0][0]} {pts[0][1]}"
        px, py = pts[0]
        for x, y in pts[1:]:
            s += f"l{x - px} {y - py}"; px, py = x, y
        out.append(s + "z")
    return "".join(out)


def tract_maps():
    import shapefile  # pyshp
    tr = json.load(open(os.path.join(OUT, "hpi_tracts.json")))
    order = ["hpiscore"] + [d for d, _, _ in DOMAINS]
    pct = {}
    for i, var in enumerate(order):
        for r in tr.get(var, {}).get("rows", []):
            g = str(r["geoid"]).zfill(11)
            rec = pct.setdefault(g, {"n": str(r.get("name") or ""), "pop": r.get("population"), "p": [None] * len(order)})
            rec["p"][i] = _pct(r.get("percentile"))
    z = zipfile.ZipFile(io.BytesIO(requests.get(TRACT_SHP, timeout=300).content))
    base = [n[:-4] for n in z.namelist() if n.endswith(".shp")][0]
    sf = shapefile.Reader(shp=io.BytesIO(z.read(base + ".shp")), dbf=io.BytesIO(z.read(base + ".dbf")))
    fields = [f[0] for f in sf.fields[1:]]
    by_county = {}
    for sr in sf.iterShapeRecords():
        rec = dict(zip(fields, sr.record))
        g = rec["GEOID"]
        if g[:5] not in NAME_OF: continue
        parts = list(sr.shape.parts) + [len(sr.shape.points)]
        rings = [sr.shape.points[parts[i]:parts[i + 1]] for i in range(len(parts) - 1)]
        by_county.setdefault(g[:5], []).append((g, rings))
    os.makedirs(os.path.join(OUT, "hpi_geo"), exist_ok=True)
    for fips, tracts in by_county.items():
        lons = [p[0] for _, rs in tracts for r in rs for p in r]; lats = [p[1] for _, rs in tracts for r in rs for p in r]
        x0, x1, y0, y1 = min(lons), max(lons), min(lats), max(lats)
        k = math.cos(math.radians((y0 + y1) / 2))
        sc = MAP_W / ((x1 - x0) * k)
        h = int(math.ceil((y1 - y0) * sc))
        proj = lambda lon, lat: (int(round((lon - x0) * k * sc)), int(round((y1 - lat) * sc)))
        rows = []
        for g, rings in sorted(tracts):
            info = pct.get(g, {"n": g[5:].lstrip("0"), "pop": None, "p": [None] * len(order)})
            rows.append([g, info["n"], info["pop"], info["p"], _path(rings, proj)])
        json.dump({"county": NAME_OF[fips], "w": MAP_W, "h": h, "layers": order, "tracts": rows},
                  open(os.path.join(OUT, "hpi_geo", fips + ".json"), "w"), separators=(",", ":"))
    sizes = {NAME_OF[f]: os.path.getsize(os.path.join(OUT, "hpi_geo", f + ".json")) // 1024 for f in by_county}
    print("Tract maps (KB):", sizes)


if __name__ == "__main__":
    if sys.argv[1:] == ["shape"]: shape()
    elif sys.argv[1:] == ["maps"]: tract_maps()
    else: main()

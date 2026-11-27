"""Pull California Healthy Places Index (HPI) data from the HPI API (Public Health Alliance of Southern California).

Reads the API key from the HPI_API_KEY environment variable (a GitHub secret). The key is never written to a file
or printed. Used with the Alliance's written permission to display HPI values on the dashboard.

Writes:
  data/out/hpi_catalog.json   indicator list with titles, sources, units, and years (from the public API documentation page)
  data/out/hpi_counties.json  every HPI indicator for all California counties and the state, latest year
  data/out/hpi_tracts.json    HPI score and domains for the census tracts in the dashboard counties (2020 tracts)
  data/out/hpi_probe.json     the shape of each API response (fields and a sample row), for checking the pull
"""
import os, sys, json, re, time
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
    json.dump(probe, open(os.path.join(OUT, "hpi_probe.json"), "w"), indent=1)
    errors = [k for k, v in probe.items() if "error" in v]
    print(f"Indicators: {len(cat)}. Calls with errors: {len(errors)}")
    for k in errors: print("  ", k, probe[k]["error"])
    if len(errors) > len(probe) // 2: sys.exit(1)


if __name__ == "__main__":
    main()

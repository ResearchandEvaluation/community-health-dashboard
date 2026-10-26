"""Shared helpers for CKAN pulls from data.chhs.ca.gov (PHIL Community Health Data Dashboard)."""
import os
import json, os, urllib.parse, urllib.request, ssl

CA_BUNDLE = "/root/.ccr/ca-bundle.crt" if os.path.exists("/root/.ccr/ca-bundle.crt") else None
CTX = ssl.create_default_context(cafile=CA_BUNDLE)
CKAN = "https://data.chhs.ca.gov/api/3/action"
COUNTIES = ["Butte", "Colusa", "Del Norte", "Glenn", "Humboldt", "Lake", "Mendocino", "Shasta",
            "Tehama", "Trinity", "Siskiyou", "Los Angeles", "San Bernardino", "Sonoma", "Marin",
            "Sutter", "Napa"]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "out")
POP_RESOURCE = "88433daa-9abf-4ebc-bc26-a44c85c4031d"  # CDPH LHJ Age-Race-Sex population, Vintage 2026.2


def get(url):
    with urllib.request.urlopen(url, context=CTX, timeout=120) as r:
        return json.load(r)


def sql(query):
    d = get(CKAN + "/datastore_search_sql?" + urllib.parse.urlencode({"sql": query}))
    if not d.get("success"):
        raise RuntimeError(d)
    return d["result"]["records"]


def inlist(vals):
    return ",".join("'" + v.replace("'", "''") + "'" for v in vals)


def county_population(years):
    """Total population by county and year from the CDPH population file (county_indicator = 1 rows
    are whole counties, including Los Angeles with Long Beach and Pasadena). Returns
    {county: {year: pop}} plus key 'California' = sum of all 58 counties."""
    recs = sql(f'SELECT county_lhj, year, SUM(population::numeric) AS pop FROM "{POP_RESOURCE}" '
               f"WHERE county_indicator = '1' AND year IN ({inlist(years)}) GROUP BY county_lhj, year")
    out = {}
    for r in recs:
        out.setdefault(r["county_lhj"], {})[r["year"]] = float(r["pop"])
    ca = {}
    for c, d in out.items():
        for y, p in d.items():
            ca[y] = ca.get(y, 0.0) + p
    out["California"] = ca
    return out


def write(key, obj):
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/{key}.json", "w") as f:
        json.dump(obj, f, indent=2)
    print("wrote", f"{OUT}/{key}.json")

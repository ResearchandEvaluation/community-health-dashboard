"""opioidED: opioid overdose emergency department (ED) visits and hospitalizations, age-adjusted rate per 100,000
residents, by county. Published in the DHCS Behavioral Health Public County Profile, 'BH Reporting' resource
(4b05457d-d1ae-4bd7-b2e8-d8579d218ffc), DIMENSION 'Opioid Overdose'. DHCS publishes no statewide value, so no
California comparison is shown. Cells DHCS suppresses for small numbers show as suppressed. Published values only."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chhs_common import sql

RES = "4b05457d-d1ae-4bd7-b2e8-d8579d218ffc"
SRC = "https://data.chhs.ca.gov/dataset/bh-county-profile/resource/" + RES
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "out")
COUNTIES = ["Butte", "Colusa", "Del Norte", "Glenn", "Humboldt", "Lake", "Mendocino", "Shasta", "Tehama", "Trinity",
            "Siskiyou", "Los Angeles", "San Bernardino", "Sonoma", "Marin", "Sutter", "Napa"]
MEASURES = [("ED Visit", "opioid_ed_rate", "Opioid overdose emergency department visits per 100,000 residents"),
            ("Hospitalization", "opioid_hosp_rate", "Opioid overdose hospitalizations per 100,000 residents")]


def main():
    rows = sql(f'SELECT "COUNTY_NAME","RPT_PERIOD_YEAR","DIMENSION_DTL","VALUE","ANNOTATION_DESC" FROM "{RES}" '
               f'WHERE "DIMENSION" = \'Opioid Overdose\'')
    out = []
    for key, mid, label in MEASURES:
        mine = [r for r in rows if key in r["DIMENSION_DTL"]]
        year = max(r["RPT_PERIOD_YEAR"] for r in mine)
        vals, all58 = {}, {}
        for r in mine:
            if r["RPT_PERIOD_YEAR"] != year:
                continue
            c = r["COUNTY_NAME"].replace(" County", "")
            v = r["VALUE"]
            if v in ("*", None, ""):
                vals[c] = "suppressed" if (r.get("ANNOTATION_DESC") or v == "*") else None
            else:
                vals[c] = float(v); all58[c] = float(v)
        out.append({"id": mid, "label": label, "unit": "rate per 100,000", "period": year,
                    "values": {c: vals.get(c) for c in COUNTIES}, "california": None, "california_source": "published",
                    "higher_is_worse": True, "source_url": SRC, "all_ca_counties": all58,
                    "note": ("Age-adjusted rate of emergency department visits or hospitalizations for any opioid-related "
                             "overdose, as published by DHCS in the Behavioral Health Public County Profile. DHCS publishes "
                             "no statewide rate. Suppressed means DHCS withheld a small number.")})
    json.dump({"key": "opioidED", "measures": out}, open(os.path.join(OUT, "opioidED.json"), "w"), indent=1)
    print("wrote opioidED", out[0]["period"], out[0]["values"]["Lake"], len(out[0]["all_ca_counties"]))


if __name__ == "__main__":
    main()

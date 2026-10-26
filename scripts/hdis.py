"""Pull California System Performance Measures by Continuum of Care (CoC) from the
Homelessness Data Integration System (HDIS) for the PHIL dashboard.

Writes data/out/hdis.json.
Source: data.ca.gov dataset 'ca-system-performance-measures-statewide-and-by-coc' (California Interagency
Council on Homelessness), resource "CA SPMs Prior Years and Last Twelve Months" (e02178d9-1d34-4798-9979-f50af9f1742e).
Measures (definitions from the dataset's data dictionary resource fd4ff7c8-a54a-4af2-9a13-03a8fdcc9b22):
  M1a: the number of people accessing services who experienced homelessness during the year.
  M3:  the number of people who exited homelessness into permanent housing during the year (a count; the
       dataset publishes no percent for this measure).
  M5:  the percent of people who return to homelessness within 6 months of exiting the homelessness response
       system to permanent housing (stored as a decimal fraction, for example 0.085).
The newest 'Jan YYYY - Dec YYYY' column is used; earlier columns feed the trend.
"""
import json
import os
import re
import requests

API = "https://data.ca.gov/api/3/action/datastore_search"
RES = "e02178d9-1d34-4798-9979-f50af9f1742e"
SRC = "https://data.ca.gov/dataset/ca-system-performance-measures-statewide-and-by-coc/resource/" + RES
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "out")

# County -> CoC code (HDIS/HUD naming). Los Angeles uses the publisher's 'Los Angeles County' row, which
# combines the four CoCs in the county.
COC = {
    "Butte": "CA-519", "Colusa": "CA-523", "Glenn": "CA-523", "Trinity": "CA-523",
    "Del Norte": "CA-516", "Shasta": "CA-516", "Siskiyou": "CA-516",
    "Humboldt": "CA-522", "Lake": "CA-529", "Mendocino": "CA-509", "Tehama": "CA-527",
    "Los Angeles": "Los Angeles County", "San Bernardino": "CA-609", "Sonoma": "CA-504",
    "Marin": "CA-507", "Sutter": "CA-524", "Napa": "CA-517",
}
ORDER = ["Butte", "Colusa", "Del Norte", "Glenn", "Humboldt", "Lake", "Mendocino", "Shasta", "Tehama",
         "Trinity", "Siskiyou", "Los Angeles", "San Bernardino", "Sonoma", "Marin", "Sutter", "Napa"]

COC_NOTE = ("Values are Continuum of Care (CoC) totals from the Homelessness Data Integration System (HDIS), "
            "so counties that share a CoC show the same number. County to CoC: {maps}. Los Angeles uses the "
            "publisher's Los Angeles County row, which covers the Los Angeles City and County, Long Beach, "
            "Pasadena, and Glendale CoCs. California value is the published statewide row.")


def parse(v, kind):
    """Return a number, 'suppressed' for the publisher's '*', or None when blank."""
    if v in (None, ""):
        return None
    if v == "*":
        return "suppressed"
    x = float(v)
    if kind == "count":
        return int(x)
    if kind == "fraction_to_percent":
        return round(x * 100, 1)
    return x


def main():
    os.makedirs(OUT, exist_ok=True)
    r = requests.get(API, params={"resource_id": RES, "limit": 5000}, timeout=120)
    r.raise_for_status()
    res = r.json()["result"]
    cols = sorted([f["id"] for f in res["fields"] if re.fullmatch(r"Jan \d{4} - Dec \d{4}", f["id"])],
                  key=lambda c: int(c[4:8]))
    col = cols[-1]
    year = col[4:8]
    years = [c[4:8] for c in cols]
    by_metric = {}
    for x in res["records"]:
        by_metric.setdefault(x["Metric"], {})[x["Location"].strip()] = x

    def find(rows, code):
        if code == "Los Angeles County":
            return rows["Los Angeles County"]
        hits = [v for k, v in rows.items() if k.startswith(code + " ")]
        assert len(hits) == 1, code
        return hits[0]

    maps = []
    for c in ORDER:
        maps.append(f"{c}: {find(by_metric['M1a'], COC[c])['Location'].strip()}")
    coc_note = COC_NOTE.format(maps="; ".join(maps))
    la_sum = sum(int(float(find(by_metric["M1a"], c)[col])) for c in ("CA-600", "CA-606", "CA-607", "CA-612"))

    def build(metric, kind, mid, label, unit, higher_is_worse, extra_note):
        rows = by_metric[metric]
        vals, trend_vals = {}, {}
        for c in ORDER:
            row = find(rows, COC[c])
            vals[c] = parse(row[col], kind)
            trend_vals[c] = [parse(row[k], kind) for k in cols]
        ca_row = rows["California"]
        return {
            "id": mid,
            "label": label,
            "unit": unit,
            "period": year,
            "values": vals,
            "california": parse(ca_row[col], kind),
            "california_source": "published",
            "higher_is_worse": higher_is_worse,
            "note": extra_note + " " + coc_note,
            "source_url": SRC,
            "trend": {"periods": years, "values": trend_vals,
                      "california": [parse(ca_row[k], kind) for k in cols]},
        }

    measures = [
        build("M1a", "count", "hdis_people_accessing_services",
              ("People accessing homeless response services who experienced homelessness during the year "
               "(California System Performance Measure 1a), Continuum of Care total"),
              "count", None,
              ("Published by the California Interagency Council on Homelessness (Cal ICH) from HDIS, calendar "
               f"years {years[0]} to {year}. The Los Angeles County row is smaller than the sum of the four "
               f"Los Angeles CoC rows ({la_sum:,}) because people served in more than one CoC are counted once.")),
        build("M3", "count", "hdis_exits_to_permanent_housing",
              ("People who exited homelessness into permanent housing during the year (California System "
               "Performance Measure 3), Continuum of Care total"),
              "count", False,
              ("Published by the California Interagency Council on Homelessness (Cal ICH) from HDIS, calendar "
               f"years {years[0]} to {year}. Measure 3 counts people who exited the homelessness response system "
               "to permanent housing plus people who moved into permanent housing within the system. Cal ICH "
               "publishes this measure as a count of people; the dataset publishes no percent of exits.")),
        build("M5", "fraction_to_percent", "hdis_returns_to_homelessness",
              ("People who returned to homelessness within 6 months of exiting the homeless response system to "
               "permanent housing (California System Performance Measure 5), Continuum of Care percent"),
              "percent", True,
              ("Published by the California Interagency Council on Homelessness (Cal ICH) from HDIS, calendar "
               f"years {years[0]} to {year}. The data dictionary defines Measure 5 as returns within 6 months of "
               "exit to permanent housing. Cal ICH stores the share as a decimal fraction (for example 0.085); "
               "the value shown is that fraction multiplied by 100 and rounded to one decimal.")),
    ]
    with open(f"{OUT}/hdis.json", "w") as f:
        json.dump({"key": "hdis", "measures": measures, "geo_note": "Continuum of Care"}, f, indent=2)
    print("wrote hdis", year)


if __name__ == "__main__":
    main()

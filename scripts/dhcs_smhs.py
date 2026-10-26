"""Child and youth Specialty Mental Health Services (SMHS) penetration (1+ services) and engagement
(5+ services) rates by county, PUBLISHED values only, for the PHIL dashboard.

Writes data/out/smhs05.json and data/out/smhsYouth.json.

Status (checked 2026-10-24): the Department of Health Care Services (DHCS) datasets on data.chhs.ca.gov
publish only counts for children and youth SMHS (TOTAL_CT, MHS1_CT, MHS5_CT), not rates:
  - Behavioral Health Program Performance Data, Demographic Data for FY's 2020-2023 (aeb088b1-...)
  - MHS Dashboard Children and Youth Demographic Datasets (ba62a75c-..., by age group)
  - Children and Youth Under the Age of 21 Performance Dashboard (4cfbafe7-..., statewide only)
The Behavioral Health Public County Profile, Demographics file (305e64c3-...) has county values by
SMHS age group (0-5, 6-11, 12-17, 18-20) with no published definition, period, statewide value,
engagement measure, or 0 to 20 total, so it is not used.
PHIL policy is to show published values only, so the files carry the published DHCS COUNTS of children
with 1 or more and 5 or more SMHS services (newest fiscal year, county rows and the Statewide row).
Ages 0 to 2 and 3 to 5 stay separate because DHCS publishes no combined 0 to 5 group. This script re-checks
the resources each run and stops with a message if any rate or percent column appears, so the pull can be
switched to the published rate.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chhs_common import get, sql, write, COUNTIES, CKAN

CHECK = {
    "aeb088b1-3904-47c3-b5c4-de564ff1426c": "Behavioral Health Program Performance Data, Demographic Data",
    "ba62a75c-1f4a-4576-bff6-4033bbfe2b5e": "MHS Dashboard Children and Youth Demographics by Age Group",
    "4cfbafe7-84bc-42ad-a378-6b5f0e1b3947": "Children and Youth Under 21 Performance Dashboard Demographics",
}

for rid, name in CHECK.items():
    fields = [f["id"] for f in get(f"{CKAN}/datastore_search?limit=0&resource_id={rid}")["result"]["fields"]]
    hits = [f for f in fields if any(k in f.upper() for k in ("RATE", "PCT", "PERCENT", "PENETRATION"))]
    if hits:
        sys.exit(f"{name} ({rid}) now has rate columns {hits}: update dhcs_smhs.py to use the published rate.")

RES = "aeb088b1-3904-47c3-b5c4-de564ff1426c"
SRC = f"https://data.chhs.ca.gov/dataset/behavioral-health-program-performance-data/resource/{RES}"
base = (f'FROM "{RES}" WHERE "MEDI_CAL_DELIVERY_SYSTEM" = \'SMHS\' AND "POP_CAT" = \'Children and Youth\' '
        f'AND "DEMO_CAT" = \'Age\'')
fy = max(r["fy"] for r in sql(f'SELECT DISTINCT "FISCAL_YEAR" AS fy {base}'))
rows = sql(f'SELECT * {base} AND "FISCAL_YEAR" = \'{fy}\'')
idx = {}
for r in rows:
    k = (r["Health Care Delivery System"].strip(), r["DEMO_GRP"])
    assert k not in idx, k
    idx[k] = r
y1, y2 = fy.split("/")
period = f"FY {y1}-{y2}"


def cell(geo, grp, col):
    r = idx.get((geo, grp))
    if r is None:
        return None
    if r.get(col + "_ANNOT") not in (None, ""):
        return "suppressed"
    v = r.get(col)
    return None if v in (None, "") else int(float(v))


NOTE = ("Published count from the Department of Health Care Services (DHCS) Behavioral Health Program Performance Data, "
        "county Mental Health Plan rows, children and youth population, {fy}. DHCS publishes counts, not rates, for this "
        "measure. Values marked suppressed were suppressed by DHCS for small numbers or as complementary cells. "
        "California value is the count published in the DHCS Statewide row.{extra}")

specs = {
    "smhs05": [("A1 Children 0-2", "ages 0 to 2", "0_2"), ("A2 Children 3-5", "ages 3 to 5", "3_5")],
    "smhsYouth": [("A0 All", "ages 0 to 20", "0_20")],
}
for key, groups in specs.items():
    measures = []
    for col, kind, lab in (("MHS1_CT", "1plus", "1 or more"), ("MHS5_CT", "5plus", "5 or more")):
        for grp, ages, aid in groups:
            extra = (" DHCS publishes ages 0 to 2 and 3 to 5 as separate groups and no combined ages 0 to 5 count, "
                     "so the two groups are shown separately." if key == "smhs05" else
                     " Ages 0 to 20 is the DHCS 'All' age group for the children and youth population.")
            measures.append({
                "id": f"smhs_{kind}_count_{aid}",
                "label": (f"Medi-Cal children {ages} who received {lab} Specialty Mental Health Services (SMHS) "
                          "services in the fiscal year"),
                "unit": "count",
                "period": period,
                "values": {c: cell(c, grp, col) for c in COUNTIES},
                "california": cell("Statewide", grp, col),
                "california_source": "published",
                "higher_is_worse": None,
                "note": NOTE.format(fy=period, extra=extra),
                "source_url": SRC,
            })
    write(key, {"key": key, "measures": measures})

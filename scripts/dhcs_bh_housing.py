"""Pull homelessness measures from the DHCS Behavioral Health Public County Profile for the PHIL dashboard.

Writes data/out/bhHousing.json.
Source: data.chhs.ca.gov dataset 'bh-county-profile', resource
"Behavioral Health Public County Profile - Homeless/Housing" (39b4a109-39e0-4a39-9940-6ae0d3349444).
Measures: DIMENSION 'Reduce Homelessness', the two published rates per 10,000 Medi-Cal members.
Sutter County is reported by DHCS only as the combined 'Sutter-Yuba' behavioral health county.
"""
import json
import os
import requests

API = "https://data.chhs.ca.gov/api/3/action/datastore_search"
RES = "39b4a109-39e0-4a39-9940-6ae0d3349444"
SRC = "https://data.chhs.ca.gov/dataset/bh-county-profile/resource/39b4a109-39e0-4a39-9940-6ae0d3349444"
COUNTIES = ["Butte", "Colusa", "Del Norte", "Glenn", "Humboldt", "Lake", "Mendocino", "Shasta", "Tehama",
            "Trinity", "Siskiyou", "Los Angeles", "San Bernardino", "Sonoma", "Marin", "Sutter", "Napa"]
ALIAS = {"Sutter": "Sutter-Yuba"}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "out")

MEASURES = [
    ("Rate (per 10,000) of Medi-Cal members who experienced homelessness",
     "medi_cal_homelessness_rate",
     "Medi-Cal members who experienced homelessness, rate per 10,000 Medi-Cal members"),
    ("Rate (per 10,000) of Medi-Cal members with significant BH needs who experienced homelessness",
     "medi_cal_sig_bh_homelessness_rate",
     "Medi-Cal members with significant behavioral health needs who experienced homelessness, rate per 10,000 "
     "Medi-Cal members with significant behavioral health needs"),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    r = requests.get(API, params={"resource_id": RES, "limit": 32000}, timeout=120)
    r.raise_for_status()
    recs = r.json()["result"]["records"]
    measures = []
    for dtl, mid, label in MEASURES:
        rows = [x for x in recs if x["DIMENSION"].strip() == "Reduce Homelessness" and x["DIMENSION_DTL"].strip() == dtl]
        by = {}
        periods = set()
        for x in rows:
            name = x["COUNTY_NAME"].strip()
            periods.add((x["RPT_PERIOD_TYPE"], x["RPT_PERIOD_YEAR"]))
            if x.get("ANNOTATION_CODE"):
                by[name] = "suppressed"
            else:
                by[name] = round(float(x["VALUE"]), 2)
        assert len(periods) == 1, periods
        ptype, pyear = periods.pop()
        period = f"FY {pyear.split('-')[0]}-{pyear.split('-')[1][2:]}" if ptype == "FISCAL_YEAR" else pyear
        vals = {c: by.get(ALIAS.get(c, c)) for c in COUNTIES}
        measures.append({
            "id": mid,
            "label": label,
            "unit": "rate per 10,000",
            "period": period,
            "values": vals,
            "california": by.get("State"),
            "california_source": "published",
            "higher_is_worse": True,
            "note": ("DHCS Behavioral Health Transformation 'Reduce Homelessness' measure, published in the "
                     "Behavioral Health Public County Profile as '" + dtl + "'. Sutter County value is the "
                     "combined Sutter-Yuba behavioral health county value (DHCS does not publish Sutter alone). "
                     "California value is the DHCS 'State' row."),
            "source_url": SRC,
        })
    with open(f"{OUT}/bhHousing.json", "w") as f:
        json.dump({"key": "bhHousing", "measures": measures}, f, indent=2)
    print("wrote bhHousing", [m["period"] for m in measures])


if __name__ == "__main__":
    main()

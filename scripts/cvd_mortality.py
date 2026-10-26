"""hdmort and strokemort: CDC Heart Disease / Stroke Mortality Among US Adults (35+) by State/Territory and County.
Update DATASETS to the newest release ids (search https://data.cdc.gov/api/catalog/v1?q=Heart%20Disease%20Mortality%20Data%20Among%20US%20Adults)."""
import os
from cdc_common import COUNTIES, soql, write

DATASETS = {
    "hdmort": ("mri7-5jtw", "Heart disease deaths among adults ages 35 and older", "heart disease"),
    "strokemort": ("y5ii-knwc", "Stroke deaths among adults ages 35 and older", "stroke"),
}
PERIOD = "2022 to 2024"

for key, (ds, label, word) in DATASETS.items():
    rows = soql(ds, {"$where": "locationabbr='CA' AND stratification1='Overall' AND stratification2='Overall'",
                     "$limit": 100})
    vals, ca = {}, None
    types = set()
    for r in rows:
        v = float(r["data_value"]) if r.get("data_value") not in (None, "") else None
        if r["geographiclevel"] == "State":
            ca = v
            state_type = r["data_value_type"]
        else:
            name = r["locationdesc"].replace(" County", "")
            if name in COUNTIES:
                vals[name] = v
                types.add(r["data_value_type"])
    values = {c: vals.get(c) for c in COUNTIES}
    write(key, [{
        "id": f"{key}_rate_35plus",
        "label": f"{label}, age-adjusted rate per 100,000 (3-year average)",
        "unit": "rate per 100,000",
        "period": PERIOD,
        "values": values,
        "california": ca,
        "california_source": "published",
        "higher_is_worse": True,
        "note": (f"Age-adjusted 3-year average {word} death rate for adults ages 35 and older, all sexes and racial and ethnic groups, "
                 "from the National Vital Statistics System (NVSS). County rates are spatially smoothed by CDC; the California rate "
                 "is the published state rate, which is not spatially smoothed."),
        "source_url": f"https://data.cdc.gov/resource/{ds}.json",
    }])
    print(key, types, state_type)

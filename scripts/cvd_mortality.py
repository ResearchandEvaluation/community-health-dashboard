"""hdmort and strokemort: CDC Heart Disease / Stroke Mortality Among US Adults (35+) by State/Territory and County.

CDC publishes each 3-year window as its own dataset on data.cdc.gov. This script searches the data.cdc.gov
catalog for every window, pulls the California state and county rows from each, shows the newest window as the
headline value, and keeps all windows as the published trend. No ids need updating by hand."""
import json
import os
import re
import urllib.parse
import urllib.request
from cdc_common import COUNTIES, soql, write, _ctx

TITLES = {
    "hdmort": ("Heart Disease Mortality Data Among US Adults (35+) by State/Territory and County",
               "Heart disease deaths among adults ages 35 and older", "heart disease"),
    "strokemort": ("Stroke Mortality Data Among US Adults (35+) by State/Territory and County",
                   "Stroke deaths among adults ages 35 and older", "stroke"),
}


def catalog(title):
    """All catalog entries whose name starts with the title and ends with a 'YYYY-YYYY' window."""
    url = "https://data.cdc.gov/api/catalog/v1?" + urllib.parse.urlencode({"q": title, "limit": 100})
    with urllib.request.urlopen(url, context=_ctx, timeout=120) as r:
        res = json.load(r)["results"]
    out = {}
    for item in res:
        x = item["resource"]
        name = x["name"].replace("–", "-").replace("—", "-")
        m = re.match(re.escape(title) + r"\s*-\s*(\d{4})-(\d{4})$", name)
        if not m:
            continue
        window = (int(m.group(1)), int(m.group(2)))
        out.setdefault(window, []).append(x["id"])
    return out


def pull(ds):
    rows = soql(ds, {"$where": "locationabbr='CA' AND stratification1='Overall' AND stratification2='Overall'",
                     "$limit": 100})
    vals, ca = {}, None
    for r in rows:
        v = float(r["data_value"]) if r.get("data_value") not in (None, "") else None
        if r.get("geographiclevel") == "State":
            ca = v
        else:
            name = (r.get("locationdesc") or "").replace(" County", "")
            if name in COUNTIES:
                vals[name] = v
    return vals, ca


for key, (title, label, word) in TITLES.items():
    windows = catalog(title)
    assert windows, f"no catalog windows for {title}"
    series = []
    for window in sorted(windows):
        got = None
        for ds in windows[window]:
            try:
                vals, ca = pull(ds)
            except Exception as e:  # a duplicate catalog entry can be an empty or odd copy
                print("skip", ds, e)
                continue
            if any(v is not None for v in vals.values()):
                got = (ds, vals, ca)
                break
        if got:
            series.append((window, got))
    assert series, f"no usable windows for {key}"
    (y1, y2), (ds, vals, ca) = series[-1]
    period = f"{y1} to {y2}"
    values = {c: vals.get(c) for c in COUNTIES}
    trend = {
        "periods": [f"{a} to {b}" for (a, b), _ in series],
        "values": {c: [g[1].get(c) for _, g in series] for c in COUNTIES},
        "california": [g[2] for _, g in series],
    }
    write(key, [{
        "id": f"{key}_rate_35plus",
        "label": f"{label}, age-adjusted rate per 100,000 (3-year average)",
        "unit": "rate per 100,000",
        "period": period,
        "values": values,
        "california": ca,
        "california_source": "published",
        "higher_is_worse": True,
        "trend": trend,
        "note": (f"Age-adjusted 3-year average {word} death rate for adults ages 35 and older, all sexes and racial and ethnic groups, "
                 "from the National Vital Statistics System (NVSS). County rates are spatially smoothed by CDC; the California rate "
                 "is the published state rate, which is not spatially smoothed. CDC publishes each 3-year window separately; "
                 f"the trend shows every window CDC has published, {trend['periods'][0]} through {period}."),
        "source_url": f"https://data.cdc.gov/resource/{ds}.json",
    }])
    print(key, period, "windows:", trend["periods"])

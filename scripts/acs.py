"""Pull ACS 5-year poverty and uninsured indicators (acsPov, acsChild, acsYoung).

Usage: CENSUS_API_KEY=<key> python3 acs.py [vintage]
The Census Data API now redirects unkeyed requests to missing_key.html, so a free key
from https://api.census.gov/data/key_signup.html is required. Without a key the script
writes files with null values and an explanatory note.
"""
import os
import json, math, os, sys, urllib.request, urllib.parse, urllib.error

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "out")
COUNTIES = {
    "Butte": "007", "Colusa": "011", "Del Norte": "015", "Glenn": "021", "Humboldt": "023",
    "Lake": "033", "Mendocino": "045", "Shasta": "089", "Tehama": "103", "Trinity": "105",
    "Siskiyou": "093", "Los Angeles": "037", "San Bernardino": "071", "Sonoma": "097",
    "Marin": "041", "Sutter": "101", "Napa": "055",
}
KEY = os.environ.get("CENSUS_API_KEY", "")


def latest_vintage():
    if len(sys.argv) > 1:
        return int(sys.argv[1])
    with urllib.request.urlopen("https://api.census.gov/data.json") as r:
        d = json.load(r)
    vs = [x["c_vintage"] for x in d["dataset"]
          if x.get("c_dataset") == ["acs", "acs5", "subject"] and x.get("c_vintage")]
    return max(vs)


def get(base, vars_):
    """Return {county name or 'California': {var: float}}; raises on key error."""
    res = {}
    for geo in ("county:" + ",".join(COUNTIES.values()), "state:06"):
        q = {"get": "NAME," + ",".join(vars_), "for": geo}
        if geo.startswith("county"):
            q["in"] = "state:06"
        if KEY:
            q["key"] = KEY
        url = base + "?" + urllib.parse.urlencode(q, safe=":,")

        class NoRedir(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        op = urllib.request.build_opener(NoRedir)
        try:
            with op.open(url) as r:
                rows = json.load(r)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Census API HTTP {e.code} ({e.headers.get('Location')})")
        hdr = rows[0]
        inv = {v: k for k, v in COUNTIES.items()}
        for row in rows[1:]:
            rec = dict(zip(hdr, row))
            name = inv[rec["county"]] if "county" in rec else "California"
            res[name] = {v: (float(rec[v]) if rec[v] not in (None, "") else None) for v in vars_}
    return res


def unreliable(est, moe):
    # Coefficient of variation = (MOE / 1.645) / estimate; flag if over 30 percent.
    if est is None or moe is None or moe < 0 or est == 0:
        return est == 0 and moe is not None and moe > 0
    return (moe / 1.645) / est > 0.30


def measure(mid, label, unit, period, vals, ca, ca_src, note, url):
    return {"id": mid, "label": label, "unit": unit, "period": period, "values": vals,
            "california": ca, "california_source": ca_src, "higher_is_worse": True,
            "note": note, "source_url": url}


def cv_note(flags):
    # PHIL shows published values only. The Census Bureau publishes margins of error but sets no reliability
    # cutoff, so no PHIL-defined flag is added to the note.
    return ""


def subject_measure(data, est, moe, mid, label, period, url, extra=""):
    vals = {c: data[c][est] for c in COUNTIES}
    flags = [c for c in COUNTIES if unreliable(data[c][est], data[c][moe])]
    note = " ".join(x for x in (extra, cv_note(flags)) if x)
    return measure(mid, label, "percent", period, vals, data["California"][est], "published", note, url)


def write(key, measures):
    with open(f"{OUT}/{key}.json", "w") as f:
        json.dump({"key": key, "measures": measures, "geo_note": ""}, f, indent=2)


def main():
    v = latest_vintage()
    period = f"{v - 4} to {v}"
    sub = f"https://api.census.gov/data/{v}/acs/acs5/subject"
    det = f"https://api.census.gov/data/{v}/acs/acs5"
    s1701_url = f"{sub}?get=NAME,S1701_C03_001E,S1701_C03_002E,S1701_C03_003E&for=county:*&in=state:06"
    s2701_url = f"{sub}?get=NAME,S2701_C05_001E&for=county:*&in=state:06"
    b17001_url = f"{det}?get=group(B17001)&for=county:*&in=state:06"
    try:
        s1701 = get(sub, ["S1701_C03_001E", "S1701_C03_001M", "S1701_C03_002E", "S1701_C03_002M", "S1701_C03_003E", "S1701_C03_003M"])
        s2701 = get(sub, ["S2701_C05_001E", "S2701_C05_001M"])
        below = ["B17001_004", "B17001_005", "B17001_018", "B17001_019"]
        above = ["B17001_033", "B17001_034", "B17001_047", "B17001_048"]
        bv = [x + s for x in below + above for s in ("E", "M")]
        b17 = get(det, bv)
    except RuntimeError as e:
        nullv = {c: None for c in COUNTIES}
        msg = (f"Not obtained: the U.S. Census Bureau Data API redirected unkeyed requests to its missing key page "
               f"({e}). Re-run scripts/acs.py with a CENSUS_API_KEY environment variable to populate.")
        write("acsPov", [
            measure("poverty_all", "People living below the federal poverty level", "percent", period, nullv, None, "published", msg, s1701_url),
            measure("uninsured", "People without health insurance (civilian noninstitutionalized population)", "percent", period, nullv, None, "published", msg, s2701_url)])
        write("acsChild", [measure("poverty_under18", "Children under 18 living below the federal poverty level", "percent", period, nullv, None, "published", msg, s1701_url)])
        write("acsYoung", [measure("poverty_under6", "Children under 6 living below the federal poverty level", "percent", period, nullv, None, "calculated", msg, b17001_url)])
        print(msg)
        return

    src_note = "American Community Survey (ACS) 5-year estimates."
    write("acsPov", [
        subject_measure(s1701, "S1701_C03_001E", "S1701_C03_001M", "poverty_all",
                        "People living below the federal poverty level", period, s1701_url,
                        "Table S1701, population for whom poverty status is determined."),
        subject_measure(s2701, "S2701_C05_001E", "S2701_C05_001M", "uninsured",
                        "People without health insurance (civilian noninstitutionalized population)", period, s2701_url,
                        "Table S2701, percent uninsured."),
    ])
    write("acsChild", [subject_measure(s1701, "S1701_C03_002E", "S1701_C03_002M", "poverty_under18",
                                       "Children under 18 living below the federal poverty level", period, s1701_url,
                                       "Table S1701, population under 18 for whom poverty status is determined.")])

    write("acsYoung", [subject_measure(s1701, "S1701_C03_003E", "S1701_C03_003M", "poverty_under5",
                                       "Children under 5 living below the federal poverty level", period, s1701_url,
                                       "Table S1701, children under 5 for whom poverty status is determined. The Census Bureau publishes this age group directly.")])
    print("done", v)


if __name__ == "__main__":
    main()

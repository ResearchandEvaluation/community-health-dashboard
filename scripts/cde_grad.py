"""cdeGrad: four-year adjusted cohort graduation rate by county, California Department of Education (CDE).
Files (tab-delimited) on www3.cde.ca.gov/demo-downloads/acgr/, listed at https://www.cde.ca.gov/ds/ad/filesacgr.asp.
The newest file is found by trying school years from the current year back. Rows used: Aggregate Level C (county) and
T (state), Charter School All, DASS All, Reporting Category TA (all students). Published CDE rates only."""
import datetime, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cde

BASE = "https://www3.cde.ca.gov/demo-downloads/acgr/"
FIELD = "Regular HS Diploma Graduates (Rate)"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "out")


def year_rows(yy):
    """Return {county or 'California' or 'ALL:<name>': rate} for school year ending 20yy, or None if no file."""
    url = f"{BASE}acgr{yy:02d}.txt"
    try:
        rows = list(cde.rows(url))
    except Exception:
        return None, url
    out = {}
    for r in rows:
        charter = r.get("CharterSchool", r.get("CharterYN"))
        if charter not in ("All", None) or r.get("DASS", "All") != "All" or r.get("ReportingCategory") != "TA":
            continue
        v = cde.num(r.get("RegularHSDiplomaGraduates(Rate)"))
        if r["AggregateLevel"] == "T":
            out["California"] = v
        elif r["AggregateLevel"] == "C":
            out["ALL:" + r["CountyName"]] = v
    return out, url


def main():
    yy = datetime.date.today().year % 100 + 1
    found = []
    while yy >= 17 and len(found) < 8:
        data, url = year_rows(yy)
        if data:
            found.append((yy, data, url))
        yy -= 1
    if not found:
        sys.exit("no CDE graduation files found")
    found.reverse()
    per = [f"20{y - 1:02d}-{y:02d}" for y, _, _ in found]
    newest_y, newest, newest_url = found[-1]
    vals = {c: newest.get("ALL:" + c) for c in cde.COUNTIES}
    all58 = {k[4:]: v for k, v in newest.items() if k.startswith("ALL:") and isinstance(v, (int, float))}
    m = {"id": "grad_rate", "label": "Students who graduated high school in four years", "unit": "percent",
         "period": per[-1] + " school year", "values": vals, "california": newest.get("California"),
         "california_source": "published", "higher_is_worse": False,
         "note": ("Four-year adjusted cohort graduation rate: students who earned a regular high school diploma within "
                  "four years of starting grade 9, as published by CDE."),
         "source_url": newest_url, "all_ca_counties": all58,
         "trend": {"periods": per, "values": {c: [d.get("ALL:" + c) for _, d, _ in found] for c in cde.COUNTIES},
                   "california": [d.get("California") for _, d, _ in found]}}
    json.dump({"key": "cdeGrad", "measures": [m]}, open(os.path.join(OUT, "cdeGrad.json"), "w"), indent=1)
    print("wrote cdeGrad", per[-1], vals.get("Lake"))


if __name__ == "__main__":
    main()

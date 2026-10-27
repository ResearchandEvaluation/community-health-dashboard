"""California Department of Education (CDE) chronic absenteeism and homeless student enrollment by county, with trends.
Files (tab-delimited) on www3.cde.ca.gov, linked from https://www.cde.ca.gov/ds/ad/filesabd.asp and
https://www.cde.ca.gov/ds/ad/fileshse.asp. Each school year, add the new file to the front of ABS_FILES / HSE_FILES
(check the exact file names on the index pages; CDE sometimes posts revised files with a -v2 or -v3 suffix).
Rows used: Aggregate Level C (county) and T (state), Charter School All, DASS All (files before 2021-22 have no
DASS column), Reporting Category TA (all students). Counties are matched by CDE county code.
Only published CDE values are used (no PHIL calculations)."""
import os
import csv, io, json, requests

COUNTIES = {"Butte": "04", "Colusa": "06", "Del Norte": "08", "Glenn": "11", "Humboldt": "12", "Lake": "17",
            "Mendocino": "23", "Shasta": "45", "Tehama": "52", "Trinity": "53", "Siskiyou": "47",
            "Los Angeles": "19", "San Bernardino": "36", "Sonoma": "49", "Marin": "21", "Sutter": "51", "Napa": "28"}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "out")
ABS_BASE = "https://www3.cde.ca.gov/demo-downloads/attendance/"
HSE_BASE = "https://www3.cde.ca.gov/demo-downloads/homeless/"
# Newest first. None = CDE published no data for that year.
ABS_FILES = [("2025-26", "chronicabsenteeism26.txt"), ("2024-25", "chronicabsenteeism25-v2.txt"),
             ("2023-24", "chronicabsenteeism24.txt"), ("2022-23", "chronicabsenteeism23.txt"),
             ("2021-22", "chronicabsenteeism22-v3.txt"), ("2020-21", "chronicabsenteeism21.txt"),
             ("2019-20", None), ("2018-19", "chronicabsenteeism19.txt"), ("2017-18", "chronicabsenteeism18.txt"),
             ("2016-17", "chronicabsenteeism17.txt")]
HSE_FILES = [("2025-26", "hse2526.txt"), ("2024-25", "hse2425.txt"), ("2023-24", "hse2324.txt"),
             ("2022-23", "hse2223.txt"), ("2021-22", "hse2122.txt"), ("2020-21", "hse2021.txt"),
             ("2019-20", "hse1920.txt")]


HEADERS = {"User-Agent": "PHIL-Community-Health-Dashboard/1.0 (+https://pophealthinnovationlab.org)"}


def get(url, tries=4):
    """Download with retries; the CDE server sometimes drops connections."""
    import time
    for i in range(tries):
        try:
            r = requests.get(url, timeout=120, headers=HEADERS); r.raise_for_status(); return r
        except requests.exceptions.RequestException:
            if i == tries - 1: raise
            time.sleep(15 * (i + 1))


def rows(url):
    r = get(url)
    rd = csv.DictReader(io.StringIO(r.content.decode("utf-8-sig", errors="replace")), delimiter="\t")
    for rec in rd:
        # Older files use field names without spaces (AggregateLevel, CharterYN); normalize.
        yield {k.replace("﻿", "").replace(" ", "").strip(): (v or "").strip() for k, v in rec.items() if k}


def num(v):
    v = (v or "").strip().replace(",", "")
    if v == "*": return "suppressed"
    return float(v) if v else None


def pick(url, year):
    out = {}
    inv = {v: k for k, v in COUNTIES.items()}
    for r in rows(url):
        charter = r.get("CharterSchool", r.get("CharterYN"))
        if charter != "All" or r.get("DASS", "All") != "All" or r["ReportingCategory"] != "TA": continue
        assert r["AcademicYear"] == year, (url, r["AcademicYear"])
        lvl = r["AggregateLevel"]
        if lvl == "T": out["California"] = r
        elif lvl == "C" and r["CountyCode"] in inv: out[inv[r["CountyCode"]]] = r
    return out


def series(files, base, field):
    """Return (periods oldest to newest, {county: [...]}, [california...], newest picked rows)."""
    periods, cvals, ca, newest = [], {c: [] for c in COUNTIES}, [], None
    for year, fn in reversed(files):
        periods.append(year)
        if fn is None:
            for c in COUNTIES: cvals[c].append(None)
            ca.append(None); continue
        p = pick(base + fn, year)
        for c in COUNTIES: cvals[c].append(num(p[c][field]) if c in p else None)
        ca.append(num(p["California"][field]) if "California" in p else None)
        newest = p
    return periods, cvals, ca, newest


def write(key, measures):
    json.dump({"key": key, "measures": measures}, open(f"{OUT}/{key}.json", "w"), indent=1); print("wrote", key)


def main():
    per, cv, ca, _ = series(ABS_FILES, ABS_BASE, "ChronicAbsenteeismRate")
    write("cdeAbs", [{"id": "chronic_abs_rate", "label": "Students who were chronically absent, grades K to 12", "unit": "percent",
      "period": per[-1] + " school year", "values": {c: cv[c][-1] for c in COUNTIES},
      "california": ca[-1], "california_source": "published", "higher_is_worse": True,
      "note": ("Chronically absent means missing 10 percent or more of the instructional days a student was enrolled. "
               "Rates are published by CDE for all students in the county. CDE did not publish 2019-20 absenteeism data "
               "because of the COVID-19 pandemic, and recommends caution when comparing absenteeism data across years, "
               "particularly 2020-21, when most instruction was distance learning."),
      "source_url": ABS_BASE + ABS_FILES[0][1],
      "trend": {"periods": per, "values": cv, "california": ca}}])

    per, cv, ca, _ = series(HSE_FILES, HSE_BASE, "HomelessStudentEnrollment")
    write("cdeHomeless", [{"id": "homeless_students", "label": "Students experiencing homelessness", "unit": "count",
      "period": per[-1] + " school year", "values": {c: cv[c][-1] for c in COUNTIES},
      "california": ca[-1], "california_source": "published", "higher_is_worse": True,
      "note": ("Count of students identified as experiencing homelessness at any point in the school year, as published by CDE. "
               "Includes students temporarily doubled up, in shelters, in hotels or motels, and unsheltered. Beginning in "
               "2025-26, CDE required local educational agencies to close homeless program records each year and re-verify "
               "status through the annual Housing Questionnaire; CDE states the 2025-26 decrease may reflect this change, "
               "so 2025-26 counts are not directly comparable with earlier years."),
      "source_url": HSE_BASE + HSE_FILES[0][1],
      "trend": {"periods": per, "values": cv, "california": ca}}])


if __name__ == "__main__":
    main()

"""Breakdowns by group (race and ethnicity, sex, age, student group) for the 'Your County in Detail' tab.

Writes data/out/strata.json. Every value is published by its source; PHIL calculates nothing.
A California value appears only where the same dataset publishes the same breakdown for the state.

Sources
  - CDC Heart Disease and Stroke Mortality Among US Adults (35+) by State and County (data.cdc.gov mri7-5jtw, y5ii-knwc):
    stratification1 = Sex, stratification2 = Race/Ethnicity.
  - Census American Community Survey (ACS) 5-year subject tables S1701 (poverty) and S2701 (health insurance), with
    published margins of error (90 percent confidence level).
    Each estimate carries its published margin of error. Needs the CENSUS_API_KEY environment variable.
  - California Department of Education (CDE) chronic absenteeism file (same file list as cde.py), Reporting Category codes.
  - California Department of Public Health (CDPH) asthma emergency department visit rates (data.chhs.ca.gov).
  - Department of Health Care Services (DHCS) Behavioral Health Program Performance Data, Demographic Data:
    published counts of children and youth with 1 or more specialty mental health services (SMHS).
"""
import csv, io, json, os, sys, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdc_common import soql, COUNTIES
import chhs_common
import cde

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "out")
CA = "California"


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def dim(name, groups):
    return {"name": name, "groups": groups}


def group(label, county, ca=None, caution=None, flag=None):
    g = {"label": label, "county": county}
    if ca is not None:
        g["ca"] = ca
    if caution:
        g["caution"] = caution
    if flag:
        g["flag"] = flag
    return g


# ---------- CDC heart disease and stroke deaths ----------
CDC_RACE = [("American Indian or Alaska Native", "American Indian or Alaska Native"), ("Asian", "Asian"),
            ("Black", "Black"), ("Hispanic", "Hispanic or Latino"),
            ("Native Hawaiian or Other Pacific Islander", "Native Hawaiian or Other Pacific Islander"),
            ("White", "White"), ("More than one race", "More than one race")]


def cdc_measure(ds, mid, title, topic):
    rows = soql(ds, {"$where": "locationabbr='CA'", "$limit": 5000})
    idx = {}
    for r in rows:
        geo = CA if r["geographiclevel"] == "State" else r["locationdesc"].replace(" County", "")
        v = num(r.get("data_value"))
        if v is None and "Insufficient" in (r.get("data_value_footnote") or ""):
            v = "suppressed"
        idx[(geo, r["stratification1"], r["stratification2"])] = v

    def g(label, s1, s2):
        return group(label, {c: idx.get((c, s1, s2)) for c in COUNTIES}, idx.get((CA, s1, s2)))
    return {
        "id": mid, "topic": "cardio", "title": title, "unit": "rate per 100,000", "period": "2022 to 2024",
        "higher_is_worse": True,
        "source": "Centers for Disease Control and Prevention (CDC), National Vital Statistics System",
        "source_url": f"https://data.cdc.gov/resource/{ds}.json",
        "note": ("Age-adjusted 3-year average death rate for adults ages 35 and older. CDC blends each county's rate "
                 "with nearby counties to make small-county rates more stable; the California rate is not blended. "
                 "'Suppressed' means CDC reports too few deaths to publish a rate."),
        "dims": [
            dim("Sex", [g("Female", "Female", "Overall"), g("Male", "Male", "Overall")]),
            dim("Race and ethnicity", [g(lab, "Overall", s2) for s2, lab in CDC_RACE]),
        ],
    }


# ---------- ACS subject tables ----------
ACS_COUNTIES = {"Butte": "007", "Colusa": "011", "Del Norte": "015", "Glenn": "021", "Humboldt": "023",
                "Lake": "033", "Mendocino": "045", "Shasta": "089", "Tehama": "103", "Trinity": "105",
                "Siskiyou": "093", "Los Angeles": "037", "San Bernardino": "071", "Sonoma": "097",
                "Marin": "041", "Sutter": "101", "Napa": "055"}
KEY = os.environ.get("CENSUS_API_KEY", "")


def acs_get(vintage, vars_):
    base = f"https://api.census.gov/data/{vintage}/acs/acs5/subject"
    res = {}
    for geo in ("county:" + ",".join(ACS_COUNTIES.values()), "state:06"):
        q = {"get": "NAME," + ",".join(vars_), "for": geo, "key": KEY}
        if geo.startswith("county"):
            q["in"] = "state:06"
        url = base + "?" + urllib.parse.urlencode(q, safe=":,")
        for i in range(4):
            try:
                with urllib.request.urlopen(url, timeout=150) as r:
                    rows = json.load(r)
                break
            except Exception:
                if i == 3:
                    raise
                time.sleep(10)
        hdr = rows[0]
        inv = {v: k for k, v in ACS_COUNTIES.items()}
        for row in rows[1:]:
            rec = dict(zip(hdr, row))
            name = inv[rec["county"]] if "county" in rec else CA
            res[name] = {v: num(rec[v]) for v in vars_}
    return res


def acs_measure(vintage, table, col, rows_spec, mid, title, topic, note):
    vars_ = []
    for _, _, n in rows_spec:
        vars_ += [f"{table}_{col}_{n:03d}E", f"{table}_{col}_{n:03d}M"]
    data = acs_get(vintage, vars_)
    dims = {}
    for dname, label, n in rows_spec:
        e, m = f"{table}_{col}_{n:03d}E", f"{table}_{col}_{n:03d}M"
        county = {c: (data[c][e] if data[c][e] is not None and data[c][e] >= 0 else None) for c in COUNTIES}
        moe = {c: data[c][m] for c in COUNTIES if county[c] is not None and data[c][m] is not None and data[c][m] >= 0}
        g = group(label, county, data[CA][e])
        g["moe"] = moe
        if data[CA][m] is not None and data[CA][m] >= 0:
            g["ca_moe"] = data[CA][m]
        dims.setdefault(dname, []).append(g)
    return {
        "id": mid, "topic": topic, "title": title, "unit": "percent", "period": f"{vintage - 4} to {vintage}",
        "higher_is_worse": True,
        "source": "U.S. Census Bureau, American Community Survey (ACS) 5-Year Estimates",
        "source_url": f"https://data.census.gov/table/ACSST5Y{vintage}.{table}?g=040XX00US06",
        "note": note + (" The Census Bureau publishes each estimate with a margin of error at the 90 percent confidence "
                        "level, shown as plus or minus. A larger margin means the true value may differ more from the "
                        "estimate. Small groups in small counties often have large margins of error."),
        "dims": [dim(k, v) for k, v in dims.items()],
    }


RACE_ACS = lambda first: [("Race and ethnicity", "American Indian and Alaska Native", first + 2),
                          ("Race and ethnicity", "Asian", first + 3),
                          ("Race and ethnicity", "Black or African American", first + 1),
                          ("Race and ethnicity", "Hispanic or Latino (any race)", first + 7),
                          ("Race and ethnicity", "Native Hawaiian and Other Pacific Islander", first + 4),
                          ("Race and ethnicity", "White, not Hispanic or Latino", first + 8),
                          ("Race and ethnicity", "Some other race", first + 5),
                          ("Race and ethnicity", "Two or more races", first + 6)]
POV_ROWS = ([("Age group", "Under 5", 3), ("Age group", "5 to 17", 4), ("Age group", "18 to 34", 7),
             ("Age group", "35 to 64", 8), ("Age group", "65 and older", 10),
             ("Sex", "Female", 12), ("Sex", "Male", 11)] + RACE_ACS(13))
UNINS_ROWS = ([("Age group", "Under 19", 11), ("Age group", "19 to 64", 12), ("Age group", "65 and older", 13),
               ("Sex", "Female", 15), ("Sex", "Male", 14)] + RACE_ACS(16)
              + [("Disability status", "With a disability", 35), ("Disability status", "No disability", 36)])


# ---------- CDE chronic absenteeism ----------
CDE_GROUPS = [("Race and ethnicity", [("RI", "American Indian or Alaska Native"), ("RA", "Asian"),
                                      ("RB", "African American"), ("RF", "Filipino"), ("RH", "Hispanic or Latino"),
                                      ("RP", "Pacific Islander"), ("RW", "White"), ("RT", "Two or more races")]),
              ("Sex", [("GF", "Female"), ("GM", "Male"), ("GX", "Nonbinary")]),
              ("Student group", [("SS", "Socioeconomically disadvantaged"), ("SE", "English learners"),
                                 ("SD", "Students with disabilities"), ("SF", "Foster youth"),
                                 ("SH", "Students experiencing homelessness"), ("SM", "Migrant students")]),
              ("Grade level", [("GRTK8", "Transitional kindergarten to grade 8"), ("GR912", "Grades 9 to 12")])]


def cde_measure():
    year, fn = next((y, f) for y, f in cde.ABS_FILES if f)
    url = cde.ABS_BASE + fn
    inv = {v: k for k, v in cde.COUNTIES.items()}
    idx = {}
    for r in cde.rows(url):
        charter = r.get("CharterSchool", r.get("CharterYN"))
        if charter != "All" or r.get("DASS", "All") != "All":
            continue
        lvl = r["AggregateLevel"]
        geo = CA if lvl == "T" else (inv.get(r["CountyCode"]) if lvl == "C" else None)
        if geo:
            idx[(geo, r["ReportingCategory"])] = cde.num(r["ChronicAbsenteeismRate"])
    dims = [dim(d, [group(lab, {c: idx.get((c, code)) for c in COUNTIES}, idx.get((CA, code)))
                    for code, lab in items]) for d, items in CDE_GROUPS]
    return {
        "id": "absStrata", "topic": "youth", "title": "Chronic absenteeism", "unit": "percent", "period": year,
        "higher_is_worse": True, "source": "California Department of Education (CDE)",
        "source_url": "https://www.cde.ca.gov/ds/ad/filesabd.asp",
        "note": ("Percent of students absent 10 percent or more of the days they were enrolled. "
                 "'Suppressed' means CDE withheld a small number to protect student privacy."),
        "dims": dims,
    }


# ---------- CDPH asthma ED visits ----------
ASTHMA_RACE = {"AI/AN": "American Indian or Alaska Native", "Asian/PI": "Asian or Pacific Islander",
               "NHPI": "Native Hawaiian or Pacific Islander", "Multi-race": "Multiple races"}

def asthma_measure():
    R = "94d84508-8046-40a7-b8d9-0ed73b13b697"
    rows = chhs_common.sql(f'SELECT "COUNTY","YEAR","STRATA","STRATA NAME","AGE GROUP","AGE-ADJUSTED ED VISIT RATE","COMMENT" '
                           f'FROM "{R}" WHERE "COUNTY" IN ({chhs_common.inlist(COUNTIES + [CA])})')
    newest = max(int(r["YEAR"]) for r in rows)
    idx = {}
    for r in rows:
        if int(r["YEAR"]) != newest:
            continue
        v = num(r["AGE-ADJUSTED ED VISIT RATE"])
        if v is None and (r["COMMENT"] or "").startswith("Count and rate suppressed"):
            v = "suppressed"
        if r["STRATA"] == "Race/ethnicity":
            name = ASTHMA_RACE.get(r["STRATA NAME"], r["STRATA NAME"])
        else:
            name = (r["AGE GROUP"] or "").replace("\u2013", " to ").replace("-", " to ")
            name = name.replace("+ years", " and older").replace(" years", "")
        idx[(r["COUNTY"], r["STRATA"], name)] = v

    def items(strata):
        labs = sorted({k[2] for k in idx if k[1] == strata},
                      key=lambda l: (int(l.split()[0]) if l[:1].isdigit() else 999, l))
        return [group(l, {c: idx.get((c, strata, l)) for c in COUNTIES}, idx.get((CA, strata, l))) for l in labs]
    return {
        "id": "asthmaStrata", "topic": "youth", "title": "Asthma emergency department visits", "unit": "rate per 10,000",
        "period": str(newest), "higher_is_worse": True,
        "source": "California Department of Public Health (CDPH), California Breathing Asthma Program",
        "source_url": "https://data.chhs.ca.gov/dataset/asthma-emergency-department-visit-rates/resource/" + R,
        "note": ("Age-adjusted emergency department visits with a primary diagnosis of asthma per 10,000 residents. "
                 "'Suppressed' means the publisher withheld the value. 'Not available' means there were too few visits to report a stable rate."),
        "dims": [dim("Age group", items("Age groups")), dim("Race and ethnicity", items("Race/ethnicity"))],
    }


# ---------- DHCS SMHS counts ----------
def smhs_measure():
    R = "aeb088b1-3904-47c3-b5c4-de564ff1426c"
    base = (f'FROM "{R}" WHERE "MEDI_CAL_DELIVERY_SYSTEM" = \'SMHS\' AND "POP_CAT" = \'Children and Youth\'')
    fy = max(r["fy"] for r in chhs_common.sql(f'SELECT DISTINCT "FISCAL_YEAR" AS fy {base}'))
    rows = chhs_common.sql(f'SELECT * {base} AND "FISCAL_YEAR" = \'{fy}\'')
    idx = {}
    for r in rows:
        v = "suppressed" if r.get("MHS1_CT_ANNOT") not in (None, "") else num(r.get("MHS1_CT"))
        idx[(r["Health Care Delivery System"].strip(), r["DEMO_CAT"], r["DEMO_GRP"])] = v

    def items(cat, keep):
        out = []
        for code, lab in keep:
            out.append(group(lab, {c: idx.get((c, cat, code)) for c in COUNTIES}))
        return out
    y1, y2 = fy.split("/")
    return {
        "id": "smhsStrata", "topic": "youth", "unit": "count", "period": f"FY {y1}-{y2}", "higher_is_worse": None,
        "title": "Children and youth receiving specialty mental health services",
        "source": "Department of Health Care Services (DHCS), Behavioral Health Program Performance Data",
        "source_url": "https://data.chhs.ca.gov/dataset/behavioral-health-program-performance-data/resource/" + R,
        "note": ("Number of Medi-Cal members ages 0 to 20 with 1 or more specialty mental health services (SMHS) in the "
                 "fiscal year. DHCS publishes counts, so there is no California comparison. 'Suppressed' means DHCS "
                 "withheld a small number to protect privacy."),
        "dims": [
            dim("Age group", items("Age", [("A1 Children 0-2", "0 to 2"), ("A2 Children 3-5", "3 to 5"),
                                           ("A3 Children 6-11", "6 to 11"), ("A4 Children 12-17", "12 to 17"),
                                           ("A5 Youth 18-20", "18 to 20")])),
            dim("Race and ethnicity", items("Race", [("R1 Alaskan Native or American Indian", "Alaska Native or American Indian"),
                                                     ("R2 Asian or Pacific Islander", "Asian or Pacific Islander"),
                                                     ("R3 Black", "Black"), ("R4 Hispanic", "Hispanic"),
                                                     ("R5 White", "White"), ("R6 Other", "Other")])),
            dim("Sex", items("Sex", [("S1 Female", "Female"), ("S2 Male", "Male")])),
        ],
    }


def main():
    vintage = int(os.environ.get("ACS_VINTAGE", "2024"))
    out, failed = [], []
    jobs = [
        lambda: cdc_measure("mri7-5jtw", "hdStrata", "Heart disease deaths", "cardio"),
        lambda: cdc_measure("y5ii-knwc", "strokeStrata", "Stroke deaths", "cardio"),
        lambda: acs_measure(vintage, "S1701", "C03", POV_ROWS, "povStrata", "People living below the poverty level",
                            "medi", "Percent of people below the federal poverty level."),
        lambda: acs_measure(vintage, "S2701", "C05", UNINS_ROWS, "uninsStrata", "People without health insurance",
                            "medi", "Percent of the civilian noninstitutionalized population without health insurance."),
        cde_measure, asthma_measure, smhs_measure,
    ]
    for j in jobs:
        try:
            m = j(); out.append(m); print("ok", m["id"])
        except Exception as e:
            failed.append(repr(e)); print("FAILED", repr(e))
    prev = {}
    p = os.path.join(OUT, "strata.json")
    if os.path.exists(p):
        prev = {m["id"]: m for m in json.load(open(p))["measures"]}
    ids = {m["id"] for m in out}
    out += [m for k, m in prev.items() if k not in ids]  # keep last saved data for any source that failed
    json.dump({"measures": out}, open(p, "w"), indent=1)
    print("wrote strata.json", len(out), "measures")
    if failed and not out:
        sys.exit(1)


if __name__ == "__main__":
    main()

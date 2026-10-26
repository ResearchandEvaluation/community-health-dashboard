"""Pull DHCS Behavioral Health Public County Profile measures for the PHIL dashboard.

Writes data/out/bhPerf.json, data/out/bhPlan.json and data/out/bhPen.json.
Source: data.chhs.ca.gov dataset 'bh-county-profile' (DHCS), resources
  Performance            cd6336be-070d-4045-a2ed-6501f636cb80  (Behavioral Health Transformation measures, FY 2024-25)
  Integrated Plan Status 3025720c-23b6-44d4-9fc7-71add7b71638  (county Integrated Plans, FY 2026-27 to 2028-29)
  Overview               22d05142-ec81-4975-9149-bb8d3cd8be3f  (Medi-Cal enrollment, penetration rates, managed care plans)
County names differ by file ('Butte', 'Butte County', 'BUTTE'); Sutter is reported as the combined Sutter-Yuba
behavioral health county in the Performance and Integrated Plan files ('Sutter/Yuba', 'Sutter-Yuba County').
Units for the Performance measures come from the DHCS Behavioral Health Transformation Performance Measures Report
(https://www.dhcs.ca.gov/behavioral-health-transformation/behavioral-health-transformation-performance-measures-report/).
"""
import re
import urllib.parse

from chhs_common import CKAN, COUNTIES, get, write

DATASET = "https://data.chhs.ca.gov/dataset/bh-county-profile"
RES_PERF = "cd6336be-070d-4045-a2ed-6501f636cb80"
RES_PLAN = "3025720c-23b6-44d4-9fc7-71add7b71638"
RES_OVER = "22d05142-ec81-4975-9149-bb8d3cd8be3f"
PLAN_YEAR = "2026-2027"  # first plan year; the only year with Behavioral Health Care Continuum projections


def src(rid):
    return f"{DATASET}/resource/{rid}"


def records(rid):
    d = get(CKAN + "/datastore_search?" + urllib.parse.urlencode({"resource_id": rid, "limit": 32000}))
    if not d.get("success"):
        raise RuntimeError(d)
    recs = d["result"]["records"]
    assert len(recs) == d["result"]["total"], (rid, len(recs), d["result"]["total"])
    return recs


def norm(name):
    """Normalize a DHCS county label to the dashboard county name ('Butte', 'Los Angeles', 'Sutter', 'State')."""
    n = re.sub(r"\s+", " ", (name or "").strip())
    n = re.sub(r"\s+county$", "", n, flags=re.I)
    if n.upper() in ("STATE", "STATEWIDE", "CALIFORNIA"):
        return "State"
    if re.fullmatch(r"sutter\s*[-/]\s*yuba", n, flags=re.I):
        return "Sutter"
    return n.title().replace("Del norte", "Del Norte")


def num(s):
    """Parse '30.22', '$93,607,818.00 ', '35%', '22444' to a number. Returns 'suppressed' for '*', None for blank."""
    if s is None:
        return None
    t = str(s).strip()
    if t == "":
        return None
    if t == "*":
        return "suppressed"
    t = t.replace("$", "").replace(",", "").replace("%", "").strip()
    v = float(t)
    return int(v) if v.is_integer() else round(v, 2)


def fiscal(year):
    """'2024-25' or '2026-2027' to 'FY 2024-25'."""
    a, b = year.split("-")
    return f"FY {a}-{b[-2:]}"


def fill(by):
    """Dict keyed by normalized county name to the 17-county values dict."""
    return {c: by.get(c) for c in COUNTIES}


# ---------------------------------------------------------------- bhPerf
PERF = [
    # (DIMENSION_DTL as published, id, label, unit, higher_is_worse)
    ("Follow-Up After Emergency Department Visit for Mental Illness --7 Days", "fu_ed_mental_illness_7d",
     "Emergency department visits for mental illness (Medi-Cal members age 6 and older) with a follow-up service "
     "within 7 days", "percent", False),
    ("Follow-Up After Emergency Department Visit for Substance Use --7 Days", "fu_ed_substance_use_7d",
     "Emergency department visits for substance use (Medi-Cal members age 13 and older) with a follow-up service "
     "within 7 days", "percent", False),
    ("Follow-Up After Hospitalization for Mental Illness--7 Days", "fu_hosp_mental_illness_7d",
     "Hospital discharges for mental illness (Medi-Cal members age 6 and older) with a mental health follow-up "
     "service within 7 days", "percent", False),
    ("Initiation of Substance Use Disorder (SUD) Treatment (IET-I)", "sud_treatment_initiation",
     "New substance use disorder episodes (Medi-Cal members age 13 and older) with treatment initiated within 14 days",
     "percent", False),
    ("One or More Behavioral Health (BH) Services for People with Significant Mental Health (MH) Needs",
     "one_or_more_bh_services_sig_mh",
     "Medi-Cal members with significant mental health needs who received one or more core clinical behavioral "
     "health services", "percent", False),
    ("Three or More BH Services for People with Significant Mental Health Needs", "three_or_more_bh_services_sig_mh",
     "Medi-Cal members with significant mental health needs who received three or more core clinical behavioral "
     "health services", "percent", False),
    ("Housing Services for People with Significant BH Needs Who Are At-Risk of or Experiencing Homelessness",
     "housing_services_sig_bh",
     "Medi-Cal members with significant behavioral health needs at risk of or experiencing homelessness who "
     "received at least one Medi-Cal housing Community Support", "percent", False),
    ("Children and Youth in Foster Care", "children_youth_foster_care",
     "Medi-Cal members ages 0 to 20 in foster care, rate per 10,000 Medi-Cal members ages 0 to 20",
     "rate per 10,000", True),
    ("Specialty Mental Health Services (SMHS) for Children and Youth in Foster Care", "smhs_foster_care",
     "Children and youth ages 0 to 20 in foster care enrolled in Medi-Cal who received specialty mental health "
     "services", "percent", False),
]
PERF_CODE = {  # DHCS Behavioral Health Transformation measure codes, for the note
    "fu_ed_mental_illness_7d": "BH-15", "fu_ed_substance_use_7d": "BH-14", "fu_hosp_mental_illness_7d": "IN-4",
    "sud_treatment_initiation": "BH-3", "one_or_more_bh_services_sig_mh": "BH-2",
    "three_or_more_bh_services_sig_mh": "BH-6", "housing_services_sig_bh": "HO-2",
    "children_youth_foster_care": "RC-1", "smhs_foster_care": "RC-2",
}


def bh_perf():
    recs = records(RES_PERF)
    measures = []
    for dtl, mid, label, unit, worse in PERF:
        rows = [r for r in recs if (r["DIMENSION_DTL"] or "").strip() == dtl]
        assert rows, dtl
        periods = {(r["RPT_PERIOD_TYPE"].strip().upper(), r["RPT_PERIOD_YEAR"].strip()) for r in rows}
        assert len(periods) == 1, (dtl, periods)
        ptype, pyear = periods.pop()
        period = fiscal(pyear) if ptype.startswith("FISCAL") else pyear
        by = {}
        for r in rows:
            code = (r.get("ANNOTATION_CODE") or "").strip()
            if code in ("1", "2"):
                by[norm(r["COUNTY_NAME"])] = "suppressed"
            elif code == "3":
                by[norm(r["COUNTY_NAME"])] = None
            else:
                by[norm(r["COUNTY_NAME"])] = num(r["VALUE"])
        goal = {(r["DIMENSION"] or "").strip() for r in rows}.pop()
        vals = fill(by)
        n_sup = sum(1 for v in vals.values() if v == "suppressed")
        unit_text = "a percent" if unit == "percent" else "a rate per 10,000"
        note = (f"DHCS Behavioral Health Transformation measure {PERF_CODE[mid]} under the goal '{goal}', published "
                f"in the Behavioral Health Public County Profile Performance file for {period} as {unit_text}. "
                "Sutter County value is the combined Sutter-Yuba behavioral health county value. "
                "California value is the DHCS 'State' row.")
        if n_sup:
            note += f" DHCS suppressed {n_sup} of the 17 counties for small numbers."
        if any(v is None for v in vals.values()):
            note += " A null value means DHCS published no value for that county."
        measures.append({
            "id": mid, "label": label, "unit": unit, "period": period, "values": vals,
            "california": by.get("State"), "california_source": "published", "higher_is_worse": worse,
            "note": note, "source_url": src(RES_PERF),
        })
    return {"key": "bhPerf", "measures": measures}


# ---------------------------------------------------------------- bhPlan
CONTINUUM = [
    ("Housing Continuum Projected Exp All BH Funding Sources", "housing", "housing continuum"),
    ("MH Continuum Projected Exp All BH Funding Sources", "mh", "mental health continuum"),
    ("SUD Continuum Projected Exp All BH Funding Sources", "sud", "substance use disorder continuum"),
]
COMPONENTS = [
    ("Behavioral Health Services and Supports", "bhsa_alloc_bhss",
     "Behavioral Health Services Act funds allocated to the Behavioral Health Services and Supports component"),
    ("Full Service Partnership", "bhsa_alloc_fsp",
     "Behavioral Health Services Act funds allocated to the Full Service Partnership component"),
    ("Housing Intervention", "bhsa_alloc_hi",
     "Behavioral Health Services Act funds allocated to the Housing Intervention component"),
]


def bh_plan():
    recs = records(RES_PLAN)
    period = fiscal(PLAN_YEAR)
    base_note = ("DHCS Behavioral Health Public County Profile Integrated Plan Status file, county Behavioral Health "
                 "Integrated Plans for the three year period FY 2026-27 to FY 2028-29, values shown for " + period + ". ")
    measures = []
    gt = [r for r in recs if r["RPT_PERIOD_YEAR"].strip() == PLAN_YEAR and (r["SERVICE_TYPE"] or "").strip() == "Grand Total"
          and (r["DIMENSION"] or "").strip() == "BH Care Continuum Projected Expenditures"]
    for dtl, short, words in CONTINUUM:
        rows = [r for r in gt if (r["DIMENSION_DTL"] or "").strip() == dtl]
        assert rows, dtl
        served = {norm(r["COUNTY_NAME"]): num(r["PROJECTED_IND_SERVED"]) for r in rows}
        cost = {norm(r["COUNTY_NAME"]): num(r["ESTIMATED_COST"]) for r in rows}
        for mid, label, unit, by in [
            (f"{short}_projected_served", f"People projected to be served in the {words}, all behavioral health "
             f"funding sources", "count", served),
            (f"{short}_estimated_cost", f"Estimated cost of the {words}, all behavioral health funding sources",
             "dollars", cost),
        ]:
            vals = fill(by)
            n_sup = sum(1 for v in vals.values() if v == "suppressed")
            note = (base_note + f"'Grand Total' row of the '{dtl}' projection. Sutter County value is the combined "
                    "Sutter-Yuba behavioral health county plan. DHCS publishes no statewide total in this file.")
            if n_sup:
                note += f" DHCS suppressed {n_sup} of the 17 counties for small numbers."
            measures.append({
                "id": mid, "label": label, "unit": unit, "period": period, "values": vals,
                "california": by.get("State"), "california_source": "published", "higher_is_worse": None,
                "note": note, "source_url": src(RES_PLAN),
            })
    comp = [r for r in recs if r["RPT_PERIOD_YEAR"].strip() == PLAN_YEAR
            and (r["DIMENSION"] or "").strip() == "Component Allocations"]
    for dtl, mid, label in COMPONENTS:
        rows = [r for r in comp if (r["DIMENSION_DTL"] or "").strip() == dtl]
        assert rows, dtl
        by = {}
        for r in rows:
            code = (r.get("ANNOTATION_CODE") or "").strip()
            by[norm(r["COUNTY_NAME"])] = "suppressed" if code in ("1", "2") else num(r["FINAL_ADJUSTED_ALLOCATION"])
        vals = fill(by)
        measures.append({
            "id": mid, "label": label, "unit": "percent", "period": period, "values": vals,
            "california": by.get("State"), "california_source": "published", "higher_is_worse": None,
            "note": (base_note + f"FINAL_ADJUSTED_ALLOCATION for the '{dtl}' component: the base allocation after "
                     "any Housing Intervention exemption adjustment and funding transfer request. Base allocations "
                     "under the Behavioral Health Services Act are 35 percent Behavioral Health Services and Supports, "
                     "35 percent Full Service Partnership and 30 percent Housing Intervention. Sutter County value is "
                     "the combined Sutter-Yuba behavioral health county plan. DHCS publishes no statewide value in "
                     "this file."),
            "source_url": src(RES_PLAN),
        })
    return {"key": "bhPlan", "measures": measures}


# ---------------------------------------------------------------- bhPen
def bh_pen():
    recs = records(RES_OVER)
    rows = {norm(r["COUNTY_NAME"]): r for r in recs}
    mcp = {c: (rows[c]["MCP"] or "").strip() for c in COUNTIES if c in rows}
    mcp_text = "; ".join(f"{c}: {mcp[c]}" for c in COUNTIES if mcp.get(c))
    base = ("DHCS Behavioral Health Public County Profile Overview file (published July 2026). Sutter and Yuba are "
            "listed separately in this file with identical penetration rates, which reflect the combined Sutter-Yuba "
            "behavioral health county. DHCS publishes no statewide row in this file. ")
    measures = []
    for col, mid, label, unit, period, extra, worse in [
        ("PENETRATION_RATE_COUNTY_MHS", "penetration_rate_county_mhs",
         "Medi-Cal members who received county mental health services (penetration rate)", "percent", "2024",
         "DHCS field dictionary: the percentage of Medi-Cal enrolled individuals who received county mental health "
         "services during calendar year 2024.", False),
        ("PENETRATION_RATE_SUDS", "penetration_rate_suds",
         "Medi-Cal members who received substance use disorder treatment services (penetration rate)", "percent",
         "2024", "DHCS field dictionary: the percentage of Medi-Cal enrolled individuals who received substance use "
         "disorder treatment services during calendar year 2024.", False),
        ("MEDI_CAL_ENROLLMENTS", "medi_cal_enrollment", "People enrolled in Medi-Cal", "count", "published July 2026",
         "DHCS field dictionary: the total number of individuals enrolled in Medi-Cal within the county. DHCS does "
         "not state the reference month of the count.", None),
    ]:
        by = {c: num(rows[c][col]) for c in COUNTIES if c in rows}
        vals = fill(by)
        n_sup = sum(1 for v in vals.values() if v == "suppressed")
        note = base + extra
        if n_sup:
            note += f" DHCS suppressed {n_sup} of the 17 counties for small numbers."
        note += " Medi-Cal managed care plans DHCS lists for each county: " + mcp_text + "."
        measures.append({
            "id": mid, "label": label, "unit": unit, "period": period, "values": vals,
            "california": None, "california_source": "published", "higher_is_worse": worse,
            "note": note, "source_url": src(RES_OVER),
        })
    return {"key": "bhPen", "measures": measures}


def main():
    for obj in (bh_perf(), bh_plan(), bh_pen()):
        for m in obj["measures"]:
            missing = [c for c in COUNTIES if c not in m["values"]]
            assert not missing, (obj["key"], m["id"], missing)
            assert any(isinstance(v, (int, float)) for v in m["values"].values()), (obj["key"], m["id"])
        write(obj["key"], obj)


if __name__ == "__main__":
    main()

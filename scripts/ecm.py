"""Enhanced Care Management (ECM) and Community Supports data for the dashboard.

Pulls the DHCS ECM and Community Supports Quarterly Implementation Report tables from the
DHCS ArcGIS service, keeps the 17 dashboard counties, and writes:
  data/out/ecm_tab.json   everything the ECM and Community Supports page shows
  data/out/ecm.json       the ECM reach indicator for the Access to Care page
  data/raw/ecm_<layer>.json  raw pulls, for checking

Only published DHCS values are used. "*" (suppressed) stays suppressed and "." means not offered.
A Community Support counts as available from a plan when the plan reports at least one provider
contract for it in the latest quarter (DHCS Chart 4.5.2). The DHCS plan elections PDF is not used:
the DHCS website blocks automated downloads.
"""
import os, sys, json, re, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
SVC = ["Housing Transition Navigation Services","Housing Deposits","Housing Tenancy and Sustaining Services","Short-Term Post-Hospitalization Housing","Recuperative Care (Medical Respite)","Respite Services","Day Habilitation Programs","Nursing Facility Transition/Diversion to Assisted Living Facilities","Community Transition Services/Nursing Facility Transition to a Home","Personal Care and Homemaker Services","Environmental Accessibility Adaptations (Home Modifications)","Medically Tailored Meals or Medically Supportive Food","Sobering Centers","Asthma Remediation"]

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "out")
RAW = os.path.join(HERE, "..", "data", "raw")
BASE = "https://services7.arcgis.com/7MUwsS9z05YumJRZ/arcgis/rest/services/ECM_Community_Support_Data_Tables_for_Quarterly_Implementation_report/FeatureServer"
COUNTIES = ["Butte","Colusa","Del Norte","Glenn","Humboldt","Lake","Mendocino","Shasta","Tehama","Trinity","Siskiyou","Los Angeles","San Bernardino","Sonoma","Marin","Sutter","Napa"]
LAYERS = {"cs_contracts": 55, "cs_util": 46, "ecm_pof_contracts": 33, "ecm_reach_plan": 24, "county_total": 57,
          "ecm_pof_members": 26, "cs_members_service": 48, "ecm_reach_county": 22, "cs_util_county": 44, "totals": 14}
PLAN = {"anthem blue cross partnership plan": "Anthem Blue Cross", "blue shield of ca promise health plan": "Blue Shield of California Promise",
        "community health group partnership plan": "Community Health Group", "kern family health care": "Kern Health Systems",
        "partnership health plan of california": "Partnership HealthPlan of California", "molina healthcare of california partner plan": "Molina Healthcare of California",
        "aids healthcare foundation": "AIDS Healthcare Foundation"}
POF_FIELDS = ["Adult___Individuals_Experiencing_Homelessness_","Adult___Individuals_At_Risk_for_Avoidable_Hospital_or_ED_Utilization_","Adult___Individuals_with_Serious_Mental_Health_and_or_Substance_Use_Disorder__SUD__Needs_","Adult_Nursing_Facility_Residents_Transitioning_to_Community_","Adults_Living_in_the_Community_and_At_Risk_for_Long_Term_Care_Institutionalization_","Adult___Individuals_Transitioning_from_Incarceration__some_WPC_counties_only__","Adult___Birth_Equity","Children_and_Youth___Individuals_Experiencing_Homelessness_","Children_and_Youth___Individuals_At_Risk_for_Avoidable_Hospital_or_ED_Utilization_","Children_and_Youth____Individuals_with_Serious_Mental_Health_and_or_Substance_Use_Disorder__SUD__Needs_","Children_and_Youth___Enrolled_in_California_Children_s_Services__CCS__with_Additional_Needs_","Children_and_Youth___Involved_in_Child_Welfare_","Children_and_Youth___Individuals_Transitioning_from_Incarceration__some_WPC_counties_only__"]
F48 = {"Housing Transition Navigation Services":"Housing_Transition_Navigation_Services_","Housing Deposits":"Housing_Deposits_","Housing Tenancy and Sustaining Services":"Housing_Tenancy_and_Sustaining_Services_","Short-Term Post-Hospitalization Housing":"Short_Term_Post_Hospitalization_Housing_","Recuperative Care (Medical Respite)":"Recuperative_Care__Medical_Respite__","Respite Services":"Respite_Services_","Day Habilitation Programs":"Day_Habilitation_Programs_","Nursing Facility Transition/Diversion to Assisted Living Facilities":"Nursing_Facility_Transition_Diversion_to_Assisted_Living_Facilities_","Community Transition Services/Nursing Facility Transition to a Home":"Community_Transition_Services_Nursing_Facility_Transition_to_a_Home_","Personal Care and Homemaker Services":"Personal_Care_and_Homemaker_Services_","Environmental Accessibility Adaptations (Home Modifications)":"Environmental_Accessibility_Adaptations__Home_Modifications__","Medically Tailored Meals or Medically Supportive Food":"Medically_Tailored_Meals_or_Medically_Supportive_Food_","Sobering Centers":"Sobering_Centers_","Asthma Remediation":"Asthma_Remediation_"}

def plan(p): return PLAN.get((p or "").strip().lower(), (p or "").strip())
def val(v):
    if v is None: return None
    if isinstance(v, (int, float)): return int(v) if float(v).is_integer() else v
    v = v.strip()
    if v == "": return None
    if v == "*": return "suppressed"
    if v == ".": return "none"
    try:
        f = float(v); return int(f) if f.is_integer() else f
    except ValueError: return v
def num(v):
    try: return float(v)
    except (TypeError, ValueError): return None

def pull(layer):
    rows, off = [], 0
    while True:
        q = urllib.parse.urlencode({"where": "1=1", "outFields": "*", "f": "json", "resultOffset": off, "resultRecordCount": 2000})
        d = json.load(urllib.request.urlopen(f"{BASE}/{layer}/query?{q}", timeout=120))
        feats = d.get("features", []); rows += [f["attributes"] for f in feats]
        if not d.get("exceededTransferLimit"): break
        off += len(feats)
    os.makedirs(RAW, exist_ok=True)
    json.dump(rows, open(os.path.join(RAW, f"ecm_{layer}.json"), "w"))
    return rows

def pick_period(rows, field):
    ps = sorted({r[field] for r in rows if r.get(field)})
    return ps[-1] if ps else None

def main():
    R = {k: pull(v) for k, v in LAYERS.items()}
    # --- plan-level contracts (latest quarter)
    q55 = pick_period(R["cs_contracts"], "Reporting_Quarter_")
    q33 = pick_period(R["ecm_pof_contracts"], "Reporting_Period_")
    counties = {}
    for c in COUNTIES:
        o = {"plans": [], "offered": {}, "pending": {}, "contracts": {}, "csUtil": [], "ecmPof": {}, "ecmReach": [], "dhcsTotal": None}
        for r in R["cs_contracts"]:
            if r["County_"] == c and r["Reporting_Quarter_"] == q55:
                p = plan(r["MCP_"]); o["contracts"][p] = {s: (lambda v: -1 if v == "none" else (-2 if v == "suppressed" else (v if isinstance(v, (int, float)) else None)))(val(r[F48[s]])) for s in SVC}
        for p, cons in o["contracts"].items():
            o["offered"][p] = [sv for sv in SVC if isinstance(cons.get(sv), (int, float)) and cons[sv] > 0]
        o["plans"] = sorted(set(o["offered"]) | set(o["contracts"]))
        for r in R["cs_util"]:
            if r["County_"] == c:
                o["csUtil"].append({"plan": plan(r["MCP_"]), "offered": val(r["Number_of_Community_Support_Services_Offered__"]),
                    "members": val(r["Number_of_Members_Who_Utilized_Community_Supports_in_the_Last_12_Months_of_the_Reporting_Period_"]),
                    "services_used": val(r["Number_of_Community_Supports_Services_Utilized_in_the_Last_12_Months_of_the_Reporting_Period_"]),
                    "rate10k": val(r["Rate_of_Community_Supports_Services_Utilization_per_10_000_MCP_Members_in_the_Last_12_Months_of_the_Reporting_Period_"]),
                    "avg_members": round(num(r["Average_MCP_Members_in_the_Last_12_Months_of_the_Reporting_Period_"]) or 0)})
        for r in R["ecm_pof_contracts"]:
            if r["County_"] == c and r["Reporting_Period_"] == q33:
                o["ecmPof"][plan(r["MCP_"])] = [(lambda v: -1 if v == "none" else (-2 if v == "suppressed" else (v if isinstance(v, (int, float)) else None)))(val(r[f])) for f in POF_FIELDS] + [(lambda v: -1 if v == "none" else (-2 if v == "suppressed" else (v if isinstance(v, (int, float)) else None)))(val(r.get("Children_and_Youth___Birth_Equity", r.get("Child___Birth_Equity"))))]
        for r in R["ecm_reach_plan"]:
            if r["County_"] == c:
                o["ecmReach"].append({"plan": plan(r["MCP_"]),
                    "members": val(r["Number_of_Unique_Members_Who_Received_ECM_in_the_Last_12_Months_of_the_Reporting_Period_"]),
                    "pct": val(r["Percentage_of_MCP_Members_Who_Were_Enrolled_in_ECM_in_the_Last_12_Months_of_the_Reporting_Period_"]),
                    "u21": val(r["Number_of_Members_Under_Age_21_Enrolled_in_ECM_At_Any_Point_in_the_Last_12_Months_of_the_Reporting_Period_"]),
                    "pct_u21": val(r["Percentage_of_MCP_Members__Under_Age_21_Who_Were_Enrolled_in_ECM_in_the_Last_12_Months_of_the_Reporting_Period_"]),
                    "avg_members": round(num(r["Average_MCP_Members_in_the_Last_12_Months_of_the_Reporting_Period_"]) or 0)})
        for r in R["county_total"]:
            if r["County"] == c: o["dhcsTotal"] = r["TotalServicesOffered"]
        counties[c] = o
    # --- published county rates
    r22 = {r["County_"]: r for r in R["ecm_reach_county"]}; r44 = {r["County_"]: r for r in R["cs_util_county"]}
    def v22(c, k): return val(r22[c].get(k)) if c in r22 else None
    pub = {"county": {c: {
        "ecmPct": v22(c, "Percentage_of_MCP_Members_Who_Were_Enrolled_in_ECM_in_the_Last_12_Months_of_the_Reporting_Period_"),
        "ecmMembers": v22(c, "Number_of_Unique_Members_Enrolled_in_ECM_At_Any_Point_in_the_Last_12_Months_of_the_Reporting_Period__"),
        "avgMembers": v22(c, "Average_MCP_Members_in_the_Last_12_Months_of_the_Reporting_Period__"),
        "csRate": val(r44[c].get("Rate_of_Community_Supports_Services_Utilization_per_10_000_MCP_Members_in_the_Last_12_Months_of_the_Reporting_Period_")) if c in r44 else None,
        "csServices": val(r44[c].get("Number_of_Community_Supports_Services_Utilized_in_in_the_Last_12_Months_of_the_Reporting_Period_")) if c in r44 else None,
        "csAvail": val(r44[c].get("Number_of_Community_Supports_Available_in_County_")) if c in r44 else None} for c in COUNTIES}}
    tot = {re.sub(r"\s+", " ", r["Measure"]).strip(): r["Value"] for r in R["totals"]}
    def total(prefix):
        for k, v in tot.items():
            if k.startswith(prefix): return v
        return None
    pub["state"] = {"ecmMembers12": total("Measure 1.0.2"), "csMembers12": total("Measure 3.0.2"), "csServices12": total("Measure 3.0.5")}
    pub["allEcmPct"] = sorted(x for x in (num(r.get("Percentage_of_MCP_Members_Who_Were_Enrolled_in_ECM_in_the_Last_12_Months_of_the_Reporting_Period_")) for r in R["ecm_reach_county"]) if x is not None)
    pub["allCsRate"] = sorted(x for x in (num(r.get("Rate_of_Community_Supports_Services_Utilization_per_10_000_MCP_Members_in_the_Last_12_Months_of_the_Reporting_Period_")) for r in R["cs_util_county"]) if x is not None)
    period_end = next((r["Last_Date_In_the_Reporting_Period_"] for r in R["ecm_reach_county"] if r.get("Last_Date_In_the_Reporting_Period_")), "")
    # --- quarterly use by service and population of focus
    qs = sorted({r["Reporting_Period_"] for r in R["cs_members_service"] if r.get("Reporting_Period_")})[-4:]
    use = {c: {} for c in COUNTIES}
    def slot(c, p): return use[c].setdefault(p, {"cs": [[None] * len(qs) for _ in SVC], "pof": [[None] * len(qs) for _ in range(14)]})
    def uv(v):
        v = val(v); return "s" if v == "suppressed" else (None if v in ("none", None) else v)
    for r in R["cs_members_service"]:
        c = r["County_"]
        if c in use and r["Reporting_Period_"] in qs:
            o = slot(c, plan(r["MCP_"])); qi = qs.index(r["Reporting_Period_"])
            for i, s in enumerate(SVC): o["cs"][i][qi] = uv(r[F48[s]])
    for r in R["ecm_pof_members"]:
        c = r["County_"]
        if c in use and r.get("Quarter") in qs:
            o = slot(c, plan(r["MCP"])); qi = qs.index(r["Quarter"])
            for i, f in enumerate(POF_FIELDS + ["Child___Birth_Equity"]): o["pof"][i][qi] = uv(r.get(f, r.get("Children_and_Youth___Birth_Equity")))
    tab = {"ECMD": {"state": {}, "counties": counties, "meta": {"cs_contracts_period": q55, "ecm_pof_period": q33, "period_end": period_end}},
           "ECMD_PUB": pub, "ECM_USE": {"q": qs, "d": use}}
    os.makedirs(OUT, exist_ok=True)
    json.dump(tab, open(os.path.join(OUT, "ecm_tab.json"), "w"), separators=(",", ":"))
    year = period_end[-4:] if period_end else ""
    src = "https://data.chhs.ca.gov/dataset/chart-1-5-county-penetration-rates-for-ecm-in-the-last-12-months-of-the-reporting-period"
    json.dump({"key": "ecm", "measures": [
        {"id": "ecm_pct", "label": "Medi-Cal managed care members who received Enhanced Care Management (ECM)", "unit": "percent", "period": f"January 1 to December 31, {year}", "values": {c: pub["county"][c]["ecmPct"] for c in COUNTIES}, "california": None, "california_source": "published", "higher_is_worse": None, "note": f"DHCS county rate for {year}. DHCS publishes a statewide member count and does not publish a statewide rate.", "source_url": src},
        {"id": "ecm_members", "label": "Members who received ECM", "unit": "count", "period": f"January 1 to December 31, {year}", "values": {c: pub["county"][c]["ecmMembers"] for c in COUNTIES}, "california": pub["state"]["ecmMembers12"], "california_source": "published", "higher_is_worse": None, "note": f"DHCS count for {year}.", "source_url": src}]},
        open(os.path.join(OUT, "ecm.json"), "w"), indent=1)
    # checks
    problems = []
    for c in COUNTIES:
        if not counties[c]["plans"]: problems.append(f"{c}: no plans")
        if pub["county"][c]["ecmPct"] is None: problems.append(f"{c}: no published ECM rate")
    if problems: print("WARN", problems)
    print("ecm ok", q55, q33, period_end, len(pub["allEcmPct"]))

if __name__ == "__main__":
    main()

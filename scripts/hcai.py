"""Pull HCAI indicators from data.chhs.ca.gov (CKAN datastore) for the PHIL dashboard.

Keys produced: pqiCardiac, pqiAll, pqiKids, bhwork, edVisits.
Output: data/out/<key>.json
Re-run quarterly: python3 hcai.py  (resource ids are re-resolved from package_show each run).
"""
import json
import os
import ssl
import urllib.parse
import urllib.request

CA_BUNDLE = "/root/.ccr/ca-bundle.crt"
CTX = ssl.create_default_context(cafile=CA_BUNDLE) if os.path.exists(CA_BUNDLE) else ssl.create_default_context()
BASE = "https://data.chhs.ca.gov/api/3/action/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "out")

COUNTIES = ["Butte", "Colusa", "Del Norte", "Glenn", "Humboldt", "Lake", "Mendocino", "Shasta",
            "Tehama", "Trinity", "Siskiyou", "Los Angeles", "San Bernardino", "Sonoma", "Marin",
            "Sutter", "Napa"]


def api(action, **params):
    url = BASE + action + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, context=CTX, timeout=120) as r:
        d = json.load(r)
    if not d.get("success"):
        raise RuntimeError(d)
    return d["result"]


def sql(q):
    return api("datastore_search_sql", sql=q)["records"]


def resource_id(package, must_contain):
    """Return the datastore-active CSV resource whose name contains must_contain (newest first)."""
    res = api("package_show", id=package)["resources"]
    cands = [r for r in res if r.get("datastore_active") and must_contain.lower() in r["name"].lower()]
    cands.sort(key=lambda r: r.get("last_modified") or r.get("created") or "", reverse=True)
    return cands[0]["id"]


def endpoint(rid):
    return BASE + "datastore_search?resource_id=" + rid


def num(s):
    if s is None:
        return None
    s = str(s).replace(",", "").strip()
    if s in ("", "."):
        return None
    return float(s) if "." in s else int(s)


def write(key, measures, geo_note=None):
    obj = {"key": key, "measures": measures}
    if geo_note:
        obj["geo_note"] = geo_note
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, key + ".json"), "w") as f:
        json.dump(obj, f, indent=2)
    print("wrote", key)


# ---------------------------------------------------------------- PQI / PDI
def quality_indicator(rid, code_col, code, state_label):
    yr = sql(f'SELECT max("Year"::int) y FROM "{rid}" WHERE "{code_col}"=\'{code}\'')[0]["y"]
    rows = sql(f'SELECT "County","Count_ICD10","RiskAdjRate_ICD10","ObsRate_ICD10","AnnotationCode" '
               f'FROM "{rid}" WHERE "Year"=\'{yr}\' AND "{code_col}"=\'{code}\'')
    by = {r["County"]: r for r in rows}
    vals, suppressed, zero_or_small = {}, [], []
    for c in COUNTIES:
        r = by.get(c)
        if r is None:
            vals[c] = None
        elif r["AnnotationCode"] == "1":
            vals[c] = "suppressed"
            suppressed.append(c)
        else:
            vals[c] = num(r["RiskAdjRate_ICD10"])
            cnt = num(r["Count_ICD10"])
            if cnt is not None and cnt < 11:
                zero_or_small.append(f"{c} ({cnt} hospitalizations)")
    st = by.get(state_label)
    ca = num(st["RiskAdjRate_ICD10"]) if st else None
    return str(yr), vals, ca, suppressed, zero_or_small


def quality_trend(rid, code_col, code, state_label, current_year):
    """Year trend of published risk-adjusted rates, limited to years computed with the same AHRQ software
    version as the current year. Per HCAI dataset metadata, 2016 to 2022 were computed with software v2023;
    from v2024 onward HCAI computes each release for the most recent year only (2023 = v2024, 2024 = v2025,
    and v2025 changed risk adjustment to age, sex, and poverty with a 2022 reference population).
    Returns (trend or None, note sentence)."""
    cur = int(current_year)
    start = 2016 if cur <= 2022 else cur          # consistent software-version span ending at current year
    years = list(range(max(start, cur - 9), cur + 1))
    if len(years) < 2:
        return None, (f" No trend is shown: HCAI computed {cur} rates with a different Agency for Healthcare Research and Quality (AHRQ) "
                      "software version than earlier years (2016 to 2022 with v2023, 2023 with v2024, 2024 with v2025, which also changed "
                      "the risk adjustment model), and HCAI advises against comparing rates across software versions.")
    rows = sql(f'SELECT "Year","County","RiskAdjRate_ICD10","AnnotationCode" FROM "{rid}" '
               f'WHERE "{code_col}"=\'{code}\' AND "Year" IN ({",".join(chr(39) + str(y) + chr(39) for y in years)})')
    by = {(r["Year"], r["County"]): r for r in rows}

    def val(y, c):
        r = by.get((str(y), c))
        if r is None:
            return None
        if r["AnnotationCode"] in ("1", "2"):
            return "suppressed"
        return num(r["RiskAdjRate_ICD10"])
    trend = {"periods": [str(y) for y in years],
             "values": {c: [val(y, c) for y in years] for c in COUNTIES},
             "california": [val(y, state_label) for y in years]}
    return trend, f" Trend covers {years[0]} to {years[-1]}, all computed with the same AHRQ software version."


def build_pqi():
    pkg = "rates-of-preventable-hospitalizations-for-selected-medical-conditions-by-county"
    rid = resource_id(pkg, "Rates of Preventable Hospitalizations")
    src = endpoint(rid)
    defs = {
        "8": ("pqi08_heart_failure", "Heart failure hospitalizations among adults, Prevention Quality Indicator (PQI) 08, risk-adjusted"),
        "7": ("pqi07_hypertension", "Hypertension hospitalizations among adults, Prevention Quality Indicator (PQI) 07, risk-adjusted"),
        "90": ("pqi90_overall_composite", "Preventable hospitalizations for all conditions among adults, Prevention Quality Indicator (PQI) 90 overall composite, risk-adjusted"),
    }
    out = {}
    for code, (mid, label) in defs.items():
        yr, vals, ca, sup, small = quality_indicator(rid, "PQI", code, "STATEWIDE")
        note = ("Department of Health Care Access and Information (HCAI) risk-adjusted rate per 100,000 residents age 18 and older, "
                "by county of patient residence. California value is the dataset's STATEWIDE row.")
        if sup:
            note += " Suppressed by HCAI for small numbers: " + ", ".join(sup) + "."
        if small:
            note += " Rates based on fewer than 11 hospitalizations are statistically unstable: " + ", ".join(small) + "."
        trend, tnote = quality_trend(rid, "PQI", code, "STATEWIDE", yr)
        note += tnote
        out[code] = {"id": mid, "label": label, "unit": "rate per 100,000", "period": yr, "values": vals,
                     "california": ca, "california_source": "published", "higher_is_worse": True,
                     "note": note, "source_url": src, "trend": trend}
    write("pqiCardiac", [out["8"], out["7"]])
    write("pqiAll", [out["90"]])


def build_pdi():
    pkg = "rates-of-preventable-hospitalizations-age-18-for-selected-medical-conditions-by-county"
    rid = resource_id(pkg, "Rates of Preventable Hospitalizations (Age<18)")
    src = endpoint(rid)
    defs = {
        "90": ("pdi90_overall_composite", "Preventable hospitalizations among children age 6 to 17, Pediatric Quality Indicator (PDI) 90 overall composite, risk-adjusted", "age 6 to 17"),
        "14": ("pdi14_asthma", "Asthma hospitalizations among children age 2 to 17, Pediatric Quality Indicator (PDI) 14, risk-adjusted", "age 2 to 17"),
    }
    ms = []
    for code, (mid, label, ages) in defs.items():
        yr, vals, ca, sup, small = quality_indicator(rid, "PDI", code, "_STATEWIDE")
        note = (f"Department of Health Care Access and Information (HCAI) risk-adjusted rate per 100,000 children {ages}, "
                "by county of patient residence. California value is the dataset's statewide row.")
        if sup:
            note += " Suppressed by HCAI for small numbers: " + ", ".join(sup) + "."
        if small:
            note += " Rates based on fewer than 11 hospitalizations are statistically unstable: " + ", ".join(small) + "."
        trend, tnote = quality_trend(rid, "PDI", code, "_STATEWIDE", yr)
        note += tnote
        ms.append({"id": mid, "label": label, "unit": "rate per 100,000", "period": yr, "values": vals,
                   "california": ca, "california_source": "published", "higher_is_worse": True,
                   "note": note, "source_url": src, "trend": trend})
    write("pqiKids", ms)


# ---------------------------------------------------------------- Behavioral health and workforce
def build_bhwork():
    pkg = "behavioral-health-and-workforce"
    meta = api("package_show", id=pkg)
    rid = resource_id(pkg, "Behavioral Health and Workforce")
    src = endpoint(rid)
    rows = sql(f'SELECT DISTINCT "County","Numerator","Denominator","BinRange" FROM "{rid}"')
    # HCAI reports some small counties as combined groups, e.g. "Del Norte, Humboldt, and Trinity".
    vals, grouped = {}, {}
    for c in COUNTIES:
        hit = None
        for r in rows:
            members = [m.strip() for m in r["County"].replace(", and ", ", ").replace(" and ", ", ").split(",")]
            if c in members:
                hit = r
                if len(members) > 1:
                    grouped[c] = r["County"]
                break
        if hit is None or num(hit["Denominator"]) in (0, None):
            vals[c] = None
        else:
            vals[c] = num(hit["Numerator"])
    groups = sorted(set(grouped.values()))
    note = ("Number of inpatient hospitalizations and emergency department visits with a behavioral health diagnosis at hospitals "
            "in the county, per one health care provider license with a behavioral health specialty in the county, as published by "
            "the Department of Health Care Access and Information (HCAI). Larger ratios may indicate greater need for behavioral health providers. "
            "HCAI publishes combined values for some small counties; each member county shows the combined value: "
            + "; ".join(groups) + ". "
            "HCAI does not publish a statewide ratio or provider licenses per 100,000 population in this dataset.")
    period = "2023 hospital encounters; provider licenses as of December 3, 2024"
    tc = meta.get("temporal_coverage") or ""
    if "2023" not in tc:
        period = tc.replace("\n", "; ")
    m = {"id": "bh_encounters_per_bh_license",
         "label": "Behavioral health hospital encounters per behavioral health provider license",
         "unit": "encounters per provider license", "period": period, "values": vals,
         "california": None, "california_source": "published", "higher_is_worse": True,
         "note": note, "source_url": src}
    write("bhwork", [m], geo_note=("Hospital encounters and provider licenses are counted by county of the hospital and of the license. "
                                   "Colusa and Glenn, Del Norte, Humboldt, and Trinity, Plumas and Tehama, and Sutter and Yuba are published as combined county groups."))


# ---------------------------------------------------------------- ED encounters by facility
def build_ed():
    pkg = "hospital-emergency-department-encounters-by-facility"
    rid = resource_id(pkg, "Encounters by Facility")
    src = endpoint(rid)
    yr = sql(f'SELECT max(year::int) y FROM "{rid}"')[0]["y"]
    rows = sql(f'SELECT oshpd_id, county_name, er_service_level_desc, type, count FROM "{rid}" WHERE year=\'{yr}\'')
    enc, hosp = {}, {}
    ca_enc, ca_hosp = 0, set()
    for r in rows:
        cty = r["county_name"].title()
        n = num(r["count"]) or 0
        enc[cty] = enc.get(cty, 0) + n
        ca_enc += n
        if r["er_service_level_desc"]:
            hosp.setdefault(cty, set()).add(r["oshpd_id"])
            ca_hosp.add(r["oshpd_id"])
    v_enc = {c: enc.get(c, 0) for c in COUNTIES}
    v_hosp = {c: len(hosp.get(c, set())) for c in COUNTIES}
    zero = [c for c in COUNTIES if v_hosp[c] == 0]
    zero_txt = (" No hospital located in " + ", ".join(zero) + " reported emergency department encounters in " + str(yr) + ", so the value is 0.") if zero else ""
    m1 = {"id": "ed_encounters_total",
          "label": "Emergency department encounters at hospitals located in the county (treated and released plus admitted)",
          "unit": "count", "period": str(yr), "values": v_enc, "california": ca_enc,
          "california_source": "calculated", "higher_is_worse": None,
          "note": ("Sum of Department of Health Care Access and Information (HCAI) emergency department ED_Visit (treated and released) and ED_Admit (admitted to the same hospital) encounters across all facilities in the county, "
                   "by hospital location, including patients who live in other counties. California value is the sum across all California facilities. "
                   "Blank counts were treated as 0." + zero_txt),
          "source_url": src}
    m2 = {"id": "ed_hospitals_count",
          "label": "Hospitals with a licensed emergency department located in the county",
          "unit": "count", "period": str(yr), "values": v_hosp, "california": len(ca_hosp),
          "california_source": "calculated", "higher_is_worse": None,
          "note": ("Number of distinct facilities (by Department of Health Care Access and Information (HCAI) facility ID) in the county reporting emergency department encounters with a licensed "
                   "emergency service level (standby, basic, or comprehensive). California value is the count across all California facilities." + zero_txt),
          "source_url": src}
    write("edVisits", [m1, m2], geo_note="Hospitals located in the county (counts reflect hospital location, not patient residence).")


if __name__ == "__main__":
    build_pqi()
    build_pdi()
    build_bhwork()
    build_ed()

"""PLACES county indicators (CDC PLACES: Local Data for Better Health, County Data, 2025 release, dataset swc5-untb).

County values: PLACES model-based age-adjusted prevalence (datavaluetypeid AgeAdjPrv), Behavioral Risk Factor
Surveillance System (BRFSS) 2023 data.
California values: published by CDC, never calculated by PHIL. PLACES publishes no state value, so the California
value comes from the published BRFSS 2023 statewide age-adjusted prevalence for the same question:
  - CDC U.S. Chronic Disease Indicators (CDI), dataset hksd-2xuw, stratification Overall, AGEADJPREV; or
  - CDC BRFSS Age-Adjusted Prevalence Data (2011 to present), dataset d2rk-yvas, break_out Overall (CHD only,
    because CDI has no angina or coronary heart disease prevalence indicator).
Measures with no published matching California value (FOODINSECU, EMOTIONSPT, LONELINESS) get california = null.
Update DATASET, YEAR, and the source year filters when a newer PLACES release is posted."""
import os
from cdc_common import COUNTIES, soql, write

DATASET = "swc5-untb"
RELEASE = "2025 release"
YEAR = "2023"
SRC = f"https://data.cdc.gov/resource/{DATASET}.json"
CDI = "hksd-2xuw"
BRFSS_AA = "d2rk-yvas"
CDI_NAME = "CDC U.S. Chronic Disease Indicators (dataset hksd-2xuw)"
BRFSS_NAME = "CDC BRFSS Age-Adjusted Prevalence Data, 2011 to present (dataset d2rk-yvas)"

# PLACES measure id -> (label, higher_is_worse, state source)
# state source: ("cdi", questionid) | ("brfss", questionid, response) | None (no matching published value)
MEASURES = {
    "BPHIGH": ("High blood pressure among adults, age-adjusted", True, ("cdi", "CVD01")),
    "CHD": ("Coronary heart disease (angina or coronary heart disease) among adults, age-adjusted", True,
            ("brfss", "CVDCRHD4", "Yes")),
    "DIABETES": ("Diagnosed diabetes among adults, age-adjusted", True, ("cdi", "DIA01")),
    "OBESITY": ("Obesity among adults, age-adjusted", True, ("cdi", "NPW14")),
    "CSMOKING": ("Current cigarette smoking among adults, age-adjusted", True, ("cdi", "TOB04")),
    "BPMED": ("Taking medicine to control high blood pressure among adults with high blood pressure, age-adjusted",
              False, ("cdi", "CVD02")),
    "CHECKUP": ("Routine checkup with a doctor within the past year among adults, age-adjusted", False,
                ("cdi", "NMED12")),
    "FOODINSECU": ("Food insecurity in the past 12 months among adults, age-adjusted", True, None),
    "LACKTRPT": ("Lack of reliable transportation in the past 12 months among adults, age-adjusted", True,
                 ("cdi", "NMED06")),
    "MHLTH": ("Frequent mental distress among adults, age-adjusted", True, ("cdi", "MEN05")),
    "DEPRESSION": ("Depression among adults, age-adjusted", True, ("cdi", "MEN02")),
    "BINGE": ("Binge drinking among adults, age-adjusted", True, ("cdi", "ALC06")),
    "EMOTIONSPT": ("Lack of social and emotional support among adults, age-adjusted", True, None),
    "LONELINESS": ("Loneliness among adults, age-adjusted", True, None),
    "HOUSINSECU": ("Housing insecurity (unable to pay mortgage, rent, or utility bills) in the past 12 months "
                   "among adults, age-adjusted", True, ("cdi", "NMED05")),
    "ACCESS2": ("Lack of health insurance among adults ages 18 to 64, age-adjusted", True, ("cdi", "NMED09")),
    "LPA": ("No leisure-time physical activity among adults, age-adjusted", True, ("cdi", "NPW06")),
    "COLON_SCREEN": ("Colorectal cancer screening among adults ages 45 to 75, age-adjusted", False, ("cdi", "CAN06")),
    "DENTAL": ("Visited a dentist or dental clinic in the past year among adults, age-adjusted", False, ("cdi", "ORH06")),
}
MEASURE_YEAR = {"COLON_SCREEN": "2022", "DENTAL": "2022"}  # PLACES carries these from the 2022 BRFSS cycle
NO_STATE_REASON = {
    "FOODINSECU": "The CDC U.S. Chronic Disease Indicators (CDI) and BRFSS prevalence datasets publish no 2023 California value for this BRFSS question.",
    "LONELINESS": "The CDC U.S. Chronic Disease Indicators (CDI) and BRFSS prevalence datasets publish no 2023 California value for this BRFSS question.",
    "EMOTIONSPT": ("The CDC U.S. Chronic Disease Indicators (CDI) dataset publishes a California value for lack of social and emotional support (10.8 percent age-adjusted, "
                   "2023), but its definition differs from PLACES (PLACES counts adults who sometimes, rarely, or never "
                   "get the support they need, and California county estimates range from about 21 to 31 percent), "
                   "so it is not shown."),
}
GROUPS = {
    "places": ["BPHIGH", "CHD"],
    "placesRisk": ["DIABETES", "OBESITY", "CSMOKING"],
    "placesBPmed": ["BPMED", "CHECKUP"],
    "placesSocial": ["FOODINSECU", "LACKTRPT"],
    "placesMH": ["MHLTH", "DEPRESSION"],
    "placesAlc": ["BINGE", "CSMOKING"],
    "placesSupport": ["EMOTIONSPT", "LONELINESS"],
    "placesHousing": ["HOUSINSECU"],
    "placesAccess": ["ACCESS2", "CHECKUP"],
    "placesActivity": ["LPA"],
    "placesScreen": ["COLON_SCREEN", "DENTAL"],
}

rows = soql(DATASET, {"$where": "stateabbr='CA' and datavaluetypeid='AgeAdjPrv'", "$limit": 50000})
data = {}  # measureid -> {county: row}
for r in rows:
    data.setdefault(r["measureid"], {})[r["locationname"]] = r

cdi_rows = soql(CDI, {"$where": "locationabbr='CA' and yearstart in('2022','2023') and datasource='BRFSS' "
                                "and stratificationcategoryid1='OVERALL' and datavaluetypeid='AGEADJPREV'",
                      "$limit": 5000})
cdi = {(r["questionid"], r["yearstart"]): r for r in cdi_rows}
brfss_rows = soql(BRFSS_AA, {"$where": f"locationabbr='CA' and year='{YEAR}' and break_out='Overall'", "$limit": 5000})
brfss = {(r["questionid"], r["response"]): r for r in brfss_rows}


def state_value(mid):
    src = MEASURES[mid][2]
    if src is None:
        return None, None, None
    yr = MEASURE_YEAR.get(mid, YEAR)
    if src[0] == "cdi":
        r = cdi[(src[1], yr)]
        assert r["datavaluetype"] == "Age-adjusted Prevalence", r
        return (float(r["datavalue"]),
                f"{CDI_NAME}, indicator {src[1]} \"{r['question']}\", {yr}, age-adjusted prevalence",
                f"https://data.cdc.gov/resource/{CDI}.json?locationabbr=CA&questionid={src[1]}&yearstart={yr}"
                "&stratificationcategoryid1=OVERALL&datavaluetypeid=AGEADJPREV")
    r = brfss[(src[1], src[2])]
    assert r["data_value_type"] == "Age-adjusted Prevalence", r
    return (float(r["data_value"]),
            f"{BRFSS_NAME}, question \"{r['question']}\" (response {src[2]}), {YEAR}, age-adjusted prevalence",
            f"https://data.cdc.gov/resource/{BRFSS_AA}.json?locationabbr=CA&questionid={src[1]}&year={YEAR}"
            "&break_out=Overall")


def measure(mid):
    label, worse, _ = MEASURES[mid]
    adj = data[mid]
    years = {r["year"] for r in adj.values()}
    myear = MEASURE_YEAR.get(mid, YEAR)
    assert years == {myear}, (mid, years)
    values = {c: (float(adj[c]["data_value"]) if c in adj and adj[c].get("data_value") else None) for c in COUNTIES}
    # PHIL rule: compare only within the same data source. PLACES publishes no state value, so no California comparison
    # badge. The state's own age-adjusted BRFSS value is shown as a labeled reference only, with no better-or-worse verdict.
    sv, sdesc, surl = state_value(mid)
    ca = sv
    ca_source = "BRFSS state survey" if sv is not None else "published"
    note = (f"CDC PLACES model-based age-adjusted prevalence estimates from Behavioral Risk Factor Surveillance System (BRFSS) "
            f"{myear} data, {RELEASE}. Each county is shown among all 58 California counties in the same PLACES release.")
    reference = None
    if sv is not None:
        note += (f" PLACES publishes county estimates only. The California value is the state's age-adjusted estimate from the direct BRFSS state survey ({sdesc}). "
                 "The county value is modeled and the state value is a direct survey estimate, so small differences between them should not be read as real differences.")
    elif mid in NO_STATE_REASON:
        note += " PLACES publishes county estimates only, and " + NO_STATE_REASON[mid][0].lower() + NO_STATE_REASON[mid][1:]
    return {
        "id": mid.lower() + "_ageadj",
        "label": label,
        "unit": "percent",
        "period": myear,
        "values": values,
        "all_ca_counties": {c: float(r["data_value"]) for c, r in adj.items() if r.get("data_value")},
        "california": ca,
        "california_source": ca_source,
        "higher_is_worse": worse,
        "reference": reference,
        "note": note,
        "source_url": SRC,
    }


for key, mids in GROUPS.items():
    write(key, [measure(m) for m in mids])

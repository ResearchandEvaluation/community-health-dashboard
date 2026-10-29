"""Checks the pulled data before the site is built. Exits nonzero on a problem.
- every expected indicator file exists and has all 17 counties
- no measure is entirely empty
- no data period is OLDER than the version committed in git (a source going backwards means a pull broke)
"""
import os, json, glob, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
OUT = os.path.join(ROOT, "data", "out")
COUNTIES = ["Butte","Colusa","Del Norte","Glenn","Humboldt","Lake","Mendocino","Shasta","Tehama","Trinity","Siskiyou","Los Angeles","San Bernardino","Sonoma","Marin","Sutter","Napa"]
EXPECTED = ["hdmort","strokemort","places","placesRisk","placesBPmed","placesSocial","placesMH","placesAlc","placesSupport","placesHousing","placesAccess","od","pqiCardiac","pqiAll","pqiKids","hpsaPC","hpsaMH","acsPov","acsChild","acsYoung","medical","medicalKids","suicide","births","smhs05","smhsYouth","bhHousing","hdis","cdeAbs","cdeHomeless","ecm","ecm_tab","chdmort","diabmort","infmort","lbw","prenatal","firearm","homicide","mvc","bhPerf","bhPlan","bhPen","wic","asthmaED","acsHousing","acsVehicle","acsBroadband","acsDisability","acsLanguage","mcp_plans","strata","cdeGrad","jailRate","chrProviders","acsUnins6"]
problems = []
def committed(path):
    try:
        return json.loads(subprocess.check_output(["git", "show", f"HEAD:{path}"], cwd=ROOT, stderr=subprocess.DEVNULL))
    except Exception: return None
for key in EXPECTED:
    f = os.path.join(OUT, key + ".json")
    if not os.path.exists(f): problems.append(f"{key}: file missing"); continue
    d = json.load(open(f))
    if key == "mcp_plans":
        if len([c for c in d if c != "month"]) != 17: problems.append("mcp_plans: county count")
        continue
    if key == "strata":
        if len(d["measures"]) < 5: problems.append("strata: fewer than 5 measures")
        for m in d["measures"]:
            for dm in m["dims"]:
                for g in dm["groups"]:
                    if [c for c in COUNTIES if c not in g["county"]]: problems.append(f"strata {m['id']}: missing counties")
        continue
    if key == "ecm_tab":
        if len(d["ECMD"]["counties"]) != 17: problems.append("ecm_tab: county count")
        continue
    old = committed(f"data/out/{key}.json")
    for i, m in enumerate(d["measures"]):
        missing = [c for c in COUNTIES if c not in m["values"]]
        if missing: problems.append(f"{key}[{i}]: missing counties {missing}")
        if all(v is None for v in m["values"].values()): problems.append(f"{key}[{i}]: all values empty")
        if old and i < len(old["measures"]):
            op, np_ = str(old["measures"][i].get("period") or ""), str(m.get("period") or "")
            if op and np_ and np_ < op and op[:4].isdigit() and np_[:4].isdigit(): problems.append(f"{key}[{i}]: period went backwards {op} -> {np_}")
if problems:
    print("DATA CHECK FAILED"); [print("  " + p) for p in problems]; sys.exit(1)
print("data check ok:", len(EXPECTED), "files")

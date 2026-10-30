import json, glob, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'data', 'out')
sys.path.insert(0, os.path.join(HERE, '..', 'scripts'))
from plain import P
SKIP = {'ecm_tab', 'strata', 'bhwork', 'edVisits', 'mcp_plans', 'mcpEnroll', 'kImmun'}
SPLIT = {'bhPerf': [('bhPerfAccess', [0,1,2,3]), ('bhPerfServices', [4,5,6]), ('bhPerfFoster', [7,8])], 'bhPlan': [('bhPlanServed', [0,2,4]), ('bhPlanCost', [1,3,5]), ('bhPlanAlloc', [6,7,8])], 'bhPen': [('bhPen', [0,1])], 'wic': [('wic', [0,3])]}
D={}
for f in sorted(glob.glob(os.path.join(OUT, "*.json"))):
    if os.path.basename(f)[:-5] in SKIP: continue
    d=json.load(open(f))
    if d["key"] in SPLIT:
        for nk, idx in SPLIT[d["key"]]: D[nk]={"key":nk,"measures":[d["measures"][i] for i in idx],"geo_note":d.get("geo_note","")}
        continue
    D[d["key"]]=d
for k,d in D.items():
    keep=[]
    for m in d["measures"]:
        if k in ("hpsaPC","hpsaMH") and m["unit"]=="count": continue
        if k=="smhs05" and "0 to 2" in m["label"]: continue
        if m.get("california_source")=="calculated":
            m["california"]=None; m["note"]=(m.get("note","")+" California value not shown because the publisher does not publish one.").strip()
        keep.append(m)
    d["measures"]=keep

import re as _re
def friendly(u):
    """Turn API and file URLs into the human-readable page a partner can open."""
    if not u: return ""
    m = _re.match(r"https://api.census.gov/data/(\d{4})/acs/acs5/(subject|profile)\?get=NAME,([A-Z]+\d+)_", u)
    if m:
        y, kind, t = m.groups()
        return f"https://data.census.gov/table/{'ACSST5Y' if kind == 'subject' else 'ACSDP5Y'}{y}.{t}?g=040XX00US06$0500000"
    m = _re.match(r"https://data.cdc.gov/resource/([a-z0-9]{4}-[a-z0-9]{4})\.json", u)
    if m: return "https://data.cdc.gov/d/" + m.group(1)
    if "7c7aed93-3643-43b8-92fc-324bf8fc13f2" in u: return "https://data.chhs.ca.gov/dataset/rates-of-preventable-hospitalizations-for-selected-medical-conditions-by-county"
    if "c441b087-ed26-4652-bde1-174aa0fd5760" in u: return "https://data.chhs.ca.gov/dataset/rates-of-preventable-hospitalizations-age-18-for-selected-medical-conditions-by-county"
    if "demo-downloads/attendance" in u: return "https://www.cde.ca.gov/ds/ad/filesabd.asp"
    if "demo-downloads/acgr" in u: return "https://www.cde.ca.gov/ds/ad/filesacgr.asp"
    if "demo-downloads/homeless" in u: return "https://www.cde.ca.gov/ds/ad/fileshse.asp"
    if "countyhealthrankings.org" in u: return "https://www.countyhealthrankings.org/health-data/methodology-and-sources/data-documentation"
    if "data.hrsa.gov/DataDownload" in u: return "https://data.hrsa.gov/topics/health-workforce/shortage-areas"
    return u

MISS={"mihaDep":"cdph"}
LAB={
 ("hdis",0):"People who experienced homelessness and used homeless response services (Continuum of Care total)"}
out={k:{"m":[{"l":(P[k][i][0] if k in P and i<len(P[k]) else LAB.get((k,i),m["label"])),"u":m["unit"],"p":m["period"] or "","v":m["values"],"ca":m["california"],"n":(P[k][i][1] if k in P and i<len(P[k]) else m.get("note","")),"hp":(m.get("hp_target") if isinstance(m.get("hp_target"),(int,float)) else None),"hpo":m.get("hp_objective") or "","w":m.get("higher_is_worse"),
        "t":({"p":m["trend"]["periods"],"v":m["trend"]["values"],"ca":m["trend"].get("california")} if m.get("trend") and len(m["trend"]["periods"])>1 else None),
        "all":(sorted(m["all_ca_counties"].values()) if m.get("all_ca_counties") else None),"s":friendly(m.get("source_url",""))} for i,m in enumerate(d["measures"])],
        "g":"","miss":MISS.get(k,"")} for k,d in D.items()}
json.dump(out,open(os.path.join(HERE, "inddata.json"), "w"),separators=(",",":"))
print("ok")

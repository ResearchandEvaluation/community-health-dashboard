import json, glob, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'data', 'out')
sys.path.insert(0, os.path.join(HERE, '..', 'scripts'))
from plain import P
SKIP = {'ecm_tab', 'bhwork', 'edVisits', 'mcp_plans', 'mcpEnroll', 'kImmun'}
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
MISS={"mihaDep":"cdph"}
LAB={
 ("hdis",0):"People who experienced homelessness and used homeless response services (Continuum of Care total)"}
out={k:{"m":[{"l":(P[k][i][0] if k in P and i<len(P[k]) else LAB.get((k,i),m["label"])),"u":m["unit"],"p":m["period"] or "","v":m["values"],"ca":m["california"],"n":(P[k][i][1] if k in P and i<len(P[k]) else m.get("note","")),"hp":(m.get("hp_target") if isinstance(m.get("hp_target"),(int,float)) else None),"hpo":m.get("hp_objective") or "","w":m.get("higher_is_worse"),
        "t":({"p":m["trend"]["periods"],"v":m["trend"]["values"],"ca":m["trend"].get("california")} if m.get("trend") and len(m["trend"]["periods"])>1 else None),
        "all":(sorted(m["all_ca_counties"].values()) if m.get("all_ca_counties") else None)} for i,m in enumerate(d["measures"])],
        "g":"","miss":MISS.get(k,"")} for k,d in D.items()}
json.dump(out,open(os.path.join(HERE, "inddata.json"), "w"),separators=(",",":"))
print("ok")

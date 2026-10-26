"""Refresh the embedded data in the Claude prototype copy (Main.dc.html) from the repository's data,
so the team review copy matches the published site. Usage: python3 build/fill_prototype.py <Main.dc.html>"""
import sys, os, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
subprocess.check_call([sys.executable, os.path.join(HERE, "build_inddata.py")])
ind = open(os.path.join(HERE, "inddata.json")).read()
tab = json.load(open(os.path.join(ROOT, "data", "out", "ecm_tab.json")))
res = json.load(open(os.path.join(ROOT, "data", "manual", "resources.json"))); res.pop("_about", None)
act = json.load(open(os.path.join(ROOT, "data", "manual", "actions.json"))); act.pop("_about", None)
mcp = json.load(open(os.path.join(ROOT, "data", "out", "mcp_plans.json")))
J = lambda o: json.dumps(o, separators=(",", ":"))
blobs = {"INDD": ind, "ECM_USE": J(tab["ECM_USE"]), "MCP_PLANS": J(mcp), "ECMD_PUB": J(tab["ECMD_PUB"]), "ECMD": J(tab["ECMD"]), "RES": J(res), "ACT": J(act)}
p = sys.argv[1]; s = open(p).read()
for var, data in blobs.items():
    a = s.index(f"    var {var} = "); b = s.index(";\n", a)
    s = s[:a] + f"    var {var} = " + data + s[b:]
open(p, "w").write(s); print("prototype filled")

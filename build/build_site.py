"""Build the standalone dashboard page: public/index.html plus runtime and images.
Reads data/out/*.json (indicators), data/out/ecm_tab.json, data/manual/resources.json, data/manual/actions.json."""
import os, json, shutil, subprocess, sys, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
subprocess.check_call([sys.executable, os.path.join(HERE, "build_inddata.py")])
ind = open(os.path.join(HERE, "inddata.json")).read()
tab = json.load(open(os.path.join(ROOT, "data", "out", "ecm_tab.json")))
res = json.load(open(os.path.join(ROOT, "data", "manual", "resources.json"))); res.pop("_about", None)
act = json.load(open(os.path.join(ROOT, "data", "manual", "actions.json"))); act.pop("_about", None)
strata = json.load(open(os.path.join(ROOT, "data", "out", "strata.json")))
mcp = json.load(open(os.path.join(ROOT, "data", "out", "mcp_plans.json")))
tpl = open(os.path.join(ROOT, "site", "template.html")).read()
J = lambda o: json.dumps(o, separators=(",", ":"))
page = (tpl.replace("__INDD__", ind).replace("__ECM_USE__", J(tab["ECM_USE"])).replace("__ECMD_PUB__", J(tab["ECMD_PUB"]))
        .replace("__ECMD__", J(tab["ECMD"])).replace("__MCP_PLANS__", J(mcp)).replace("__RES__", J(res)).replace("__ACT__", J(act)).replace("__STRATA__", J(strata)).replace("__BUILD_DATE__", datetime.date.today().isoformat()))
for ph in ["__INDD__", "__ECM_USE__", "__ECMD_PUB__", "__ECMD__", "__RES__", "__ACT__", "__STRATA__", "__MCP_PLANS__"]:
    assert ph not in page, ph
if "–" in page or "—" in page:
    raise SystemExit("dash character found in page")
pub = os.path.join(ROOT, "public")
os.makedirs(os.path.join(pub, "assets"), exist_ok=True)
open(os.path.join(pub, "index.html"), "w").write(page)
shutil.copy(os.path.join(ROOT, "site", "runtime.js"), os.path.join(pub, "runtime.js"))
for f in os.listdir(os.path.join(ROOT, "site", "assets")):
    shutil.copy(os.path.join(ROOT, "site", "assets", f), os.path.join(pub, "assets", f))
open(os.path.join(pub, ".nojekyll"), "w").write("")
cname = os.path.join(ROOT, "site", "CNAME")
if os.path.exists(cname): shutil.copy(cname, os.path.join(pub, "CNAME"))
print("built public/index.html", len(page), "bytes")

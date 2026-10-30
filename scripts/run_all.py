"""Run every data pull in order. Continues after a failure, reports all failures at the end, and keeps the
last saved data for any source that fails (the run fails only if more than MAX_FAILED sources fail).
Usage: python3 scripts/run_all.py            (all sources)
       python3 scripts/run_all.py ecm places (named scripts only)"""
import os, sys, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__))
ORDER = ["cvd_mortality", "places", "od", "hcai", "hpsa", "acs", "acs_medicaid", "suicide", "chsp_more", "births", "dhcs_smhs", "dhcs_bh_housing", "hdis", "cde", "cde_grad", "vera_jail", "chr_providers", "strata", "ecm",
         "hcai_asthma", "cdph_wic", "dhcs_mcp_enrollment", "dhcs_opioid"]
names = sys.argv[1:] or ORDER
failed = []
for n in names:
    t = time.time()
    r = subprocess.run([sys.executable, os.path.join(HERE, n + ".py")], capture_output=True, text=True)
    status = "ok" if r.returncode == 0 else "FAILED"
    print(f"[{status}] {n} ({time.time() - t:.0f}s)")
    tail = (r.stdout + r.stderr).strip().splitlines()[-6:]
    for line in tail: print("    " + line)
    if r.returncode: failed.append(n)
# A source that fails keeps its last saved data, so the dashboard still publishes.
# The run is marked failed only when more than MAX_FAILED sources fail at once.
MAX_FAILED = 3
if failed:
    print("\nFailed:", ", ".join(failed))
    for n in failed:
        print(f"::warning title=Data source not refreshed::{n} failed this run. The dashboard keeps its last saved data for {n}. Re-run later or check scripts/{n}.py.")
    if len(failed) > MAX_FAILED: sys.exit(1)
    print("Continuing with last saved data for the failed sources.")
else:
    print("\nAll pulls finished.")
# Record when the data was last refreshed, for the dashboard footer.
import json, datetime
json.dump({"refreshed": datetime.date.today().isoformat(), "failed": failed}, open(os.path.join(HERE, "..", "data", "out", "_refresh.json"), "w"))

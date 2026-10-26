"""Run every data pull in order. Continues after a failure and reports all failures at the end.
Usage: python3 scripts/run_all.py            (all sources)
       python3 scripts/run_all.py ecm places (named scripts only)"""
import os, sys, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__))
ORDER = ["cvd_mortality", "places", "od", "hcai", "hpsa", "acs", "acs_medicaid", "suicide", "chsp_more", "births", "dhcs_smhs", "dhcs_bh_housing", "hdis", "cde", "ecm",
         "hcai_asthma", "cdph_wic", "dhcs_mcp_enrollment"]
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
if failed:
    print("\nFailed:", ", ".join(failed)); sys.exit(1)
print("\nAll pulls finished.")

"""Pull Medi-Cal managed care enrollment by county and plan for the PHIL dashboard and the ECM page.

Writes data/out/mcpEnroll.json and data/out/mcp_plans.json.
Source: data.chhs.ca.gov dataset 'medi-cal-managed-care-enrollment-report' (Department of Health Care Services,
Medi-Cal Managed Care Operations Division), resource 95358a7a-2c9d-41c6-a0e0-405a7e5c5f18.

The resource publishes one row per enrollment month, plan type, county, and plan. It publishes no county total
row and no statewide row, and the dashboard spec forbids summing across plans, so mcpEnroll.json carries one
measure per Medi-Cal managed care plan (medical plan types only: County Organized Health Systems, Two-Plan
commercial and local initiative, Geographic Managed Care, Regional Model, Single, Imperial and San Benito models)
with the published enrollment in each county the plan serves and null elsewhere. Program of All-Inclusive Care
for the Elderly (PACE), SCAN, Dental, Special Project, and Primary Care Case Management rows are left out of the
measures and included in mcp_plans.json with the plan type in parentheses.
Suppressed cells (annotation code 1 small numbers, 2 complementary cell) are written as "suppressed".
"""
import json
import os
from chhs_common import sql, inlist, COUNTIES, write, OUT

RES = "95358a7a-2c9d-41c6-a0e0-405a7e5c5f18"
SRC = "https://data.chhs.ca.gov/dataset/medi-cal-managed-care-enrollment-report/resource/" + RES
MEDICAL_TYPES = {"County Organized Health Systems", "COHS", "Commercial Plan (2 Plan)", "Local Initiative (2 Plan)",
                 "Two-Plan", "Geographic Managed Care", "Regional Model", "Regional", "Single", "Imperial Model",
                 "San Benito Model"}
# Publisher spells some plans more than one way; one name per organization.
ALIASES = {
    "Partnership Health Plan of California": "Partnership HealthPlan of California",
    "Kaiser Foundation Health Plan": "Kaiser Permanente",
}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


def plan_name(raw, county):
    name = raw.strip()
    suffix = "/" + county
    if name.endswith(suffix):
        name = name[: -len(suffix)].strip()
    return ALIASES.get(name, name)


def count(row):
    v = (row["Count of Enrollees"] or "").strip()
    if v:
        return int(v.replace(",", ""))
    code = (row["Count of Enrollees Annotation Code"] or "").strip()
    return "suppressed" if code in ("1", "2") else None


def main():
    newest = sql(f'SELECT MAX("Enrollment Month") AS m FROM "{RES}"')[0]["m"]
    month_label = f"{MONTHS[int(newest[5:7]) - 1]} {newest[:4]}"
    rows = sql(f'SELECT "Plan Type", "County", "Plan Name", "Count of Enrollees", '
               f'"Count of Enrollees Annotation Code" FROM "{RES}" '
               f"WHERE \"Enrollment Month\" = '{newest}' AND \"County\" IN ({inlist(COUNTIES)}) "
               f'ORDER BY "County", "Plan Type", "Plan Name"')

    plans = {c: {} for c in COUNTIES}          # for mcp_plans.json
    by_plan = {}                                # medical plans -> {county: value}
    plan_types = {}
    for r in rows:
        county = r["County"].strip()
        ptype = r["Plan Type"].strip()
        name = plan_name(r["Plan Name"], county)
        val = count(r)
        key = name if ptype in MEDICAL_TYPES else f"{name} ({ptype})"
        if key in plans[county]:
            n = 2
            while f"{key} (row {n})" in plans[county]:
                n += 1
            key = f"{key} (row {n})"
        plans[county][key] = val
        if ptype in MEDICAL_TYPES:
            if county in by_plan.get(name, {}):
                raise RuntimeError(f"two medical rows for {name} in {county}")
            by_plan.setdefault(name, {})[county] = val
            plan_types.setdefault(name, set()).add(ptype)

    measures = []
    for name in sorted(by_plan, key=lambda n: -len(by_plan[n])):
        vals = {c: by_plan[name].get(c) for c in COUNTIES}
        served = [c for c in COUNTIES if c in by_plan[name]]
        n_supp = sum(1 for c in served if vals[c] == "suppressed")
        types = ", ".join(sorted(plan_types[name]))
        measures.append({
            "id": "mcp_" + "".join(ch if ch.isalnum() else "_" for ch in name.lower()).strip("_"),
            "label": f"Medi-Cal members enrolled in {name}",
            "unit": "count",
            "period": month_label,
            "values": vals,
            "california": None,
            "california_source": "published",
            "higher_is_worse": None,
            "note": ("Published by the Department of Health Care Services (DHCS) in the Medi-Cal Managed Care "
                     f"Enrollment Report for {month_label}; plan type {types}. The report publishes enrollment "
                     "by plan and county only, with no county total and no statewide row, so each plan is its "
                     "own measure, counties the plan does not serve are null, and California is null. "
                     f"{name} serves {len(served)} of the 17 counties: " + ", ".join(served) + "." +
                     (f" DHCS suppressed the cell for {n_supp} of those counties." if n_supp else "")),
            "source_url": SRC,
        })

    write("mcpEnroll", {"key": "mcpEnroll", "measures": measures, "geo_note": ""})
    out = {c: plans[c] for c in COUNTIES}
    out["month"] = newest
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/mcp_plans.json", "w") as f:
        json.dump(out, f, indent=2)
    print("wrote", f"{OUT}/mcp_plans.json", newest, len(measures), "plan measures")


if __name__ == "__main__":
    main()

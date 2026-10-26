"""Suicide deaths: published values from the CDPH County Health Status Profiles
(data.chhs.ca.gov dataset county-health-status-profiles), Table 'Deaths Due to Suicide'.
Uses the published age-adjusted death rate per 100,000 (based on the 3-year average number of deaths)
for each county and CALIFORNIA, newest edition, plus a trend across all published editions.
No values are calculated by PHIL."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chhs_common import write, COUNTIES
from chsp_common import newest_edition, indicator_rows, published, trend

DESC = "Deaths Due to Suicide"
pub, rid, src = newest_edition()
r = indicator_rows(rid, DESC)
ca = r["California"]
assert ca["Age-Adjusted_Rate_Label"] == "Age-Adjusted Death Rate" and ca["Rate_Multiplier"] == "100000"
yrs = ca["Numerator_Year_Period"]          # e.g. 2021-2023
period = yrs.replace("-", " to ")
popyr = ca["Denominator_Year_Period"]

rate, unreliable, supp = {}, [], []
for c in COUNTIES:
    row = r.get(c)
    assert row is None or row["Numerator_Year_Period"] == yrs
    v, code = published(row, "Age-Adjusted_Rate")
    rate[c] = v
    if code == "4" and isinstance(v, float):
        unreliable.append(c)
    if v == "suppressed":
        supp.append(c)
ca_rate, _ = published(ca, "Age-Adjusted_Rate")

tr, used, unrel = trend(DESC, "Age-Adjusted_Rate", "Age-Adjusted_Rate_Label", "Age-Adjusted Death Rate", "100000")
assert tr["periods"][-1] == period and used[-1] == pub
assert [tr["values"][c][-1] for c in COUNTIES] == [rate[c] for c in COUNTIES]

edition = f"California Department of Public Health (CDPH) County Health Status Profiles {pub}"
flag = (f" CDPH flags the rate as unreliable (relative standard error of 23 percent or more) for {', '.join(unreliable)}."
        if unreliable else "")
sflag = f" CDPH suppressed the value for {', '.join(supp)}." if supp else ""
missing = [c for c in COUNTIES if rate[c] is None]
mflag = f" No value is published for {', '.join(missing)}." if missing else ""
older = "; ".join(f"{p}: {', '.join(cs)}" for p, cs in unrel.items() if p != period and p in tr["periods"])
tnote = (f" Trend shows the same published rate from the {used[0]} to {used[-1]} editions, covering the periods {tr['periods'][0]} through {period}; "
         "each edition covers a 3 year period, so adjacent periods share 2 years of deaths, and each edition uses the "
         "population estimates current when it was published."
         + (f" Rates flagged unreliable in earlier periods: {older}." if older else ""))

measures = [
    {"id": f"suicide_rate_aa_{yrs.replace('-', '_')}",
     "label": "Suicide death rate, age adjusted, 3 year average",
     "unit": "rate per 100,000", "period": period, "values": rate,
     "california": ca_rate, "california_source": "published", "higher_is_worse": True,
     "note": (f"Published age-adjusted death rate from the {edition}, deaths due to suicide by county of residence, "
              f"based on the average annual number of deaths {period} and {popyr} population.{flag}{sflag}{mflag} "
              "California value is the statewide rate published in the same CDPH table." + tnote),
     "source_url": src,
     "trend": tr},
]
write("suicide", {"key": "suicide", "measures": measures})

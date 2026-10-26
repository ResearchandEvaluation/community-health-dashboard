"""Adolescent birth rate: published values from the CDPH County Health Status Profiles
(data.chhs.ca.gov dataset county-health-status-profiles), Table 'Births to Adolescent Mothers, 15 to 19 Years Old'.
Published age-specific birth rate per 1,000 females ages 15 to 19, for each county and CALIFORNIA,
newest edition, plus a trend across all published editions. No values are calculated by PHIL."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chhs_common import write, COUNTIES
from chsp_common import newest_edition, indicator_rows, published, trend

DESC = "Births to Adolescent Mothers, 15 to 19 Years Old"
pub, rid, src = newest_edition()
r = indicator_rows(rid, DESC)
ca = r["California"]
assert ca["Rate_Multiplier"] == "1000" and ca["Rate/Percentage_Label"] == "Age-Specific Birth Rate"
yrs = ca["Numerator_Year_Period"]
period = yrs.replace("-", " to ")
popyr = ca["Denominator_Year_Period"]

vals, unreliable, supp = {}, [], []
for c in COUNTIES:
    row = r.get(c)
    assert row is None or row["Numerator_Year_Period"] == yrs
    v, code = published(row, "Rate/Percentage")
    vals[c] = v
    if code == "4" and isinstance(v, float):
        unreliable.append(c)
    if v == "suppressed":
        supp.append(c)
ca_rate, _ = published(ca, "Rate/Percentage")

tr, used, unrel = trend(DESC, "Rate/Percentage", "Rate/Percentage_Label", "Age-Specific Birth Rate", "1000")
assert tr["periods"][-1] == period and used[-1] == pub
assert [tr["values"][c][-1] for c in COUNTIES] == [vals[c] for c in COUNTIES]

edition = f"California Department of Public Health (CDPH) County Health Status Profiles {pub}"
flag = (f" CDPH flags the rate as unreliable (relative standard error of 23 percent or more) for {', '.join(unreliable)}."
        if unreliable else "")
sflag = f" CDPH suppressed the value for {', '.join(supp)}." if supp else ""
missing = [c for c in COUNTIES if vals[c] is None]
mflag = f" No value is published for {', '.join(missing)}." if missing else ""
older = "; ".join(f"{p}: {', '.join(cs)}" for p, cs in unrel.items() if p != period and p in tr["periods"])
tnote = (f" Trend shows the same published rate from the {used[0]} to {used[-1]} editions, covering the periods {tr['periods'][0]} through {period}; "
         "each edition covers a 3 year period, so adjacent periods share 2 years of births, and each edition uses the "
         "population estimates current when it was published."
         + (f" Rates flagged unreliable in earlier periods: {older}." if older else ""))

write("births", {"key": "births", "measures": [{
    "id": f"adolescent_birth_rate_15_19_{yrs.replace('-', '_')}",
    "label": "Adolescent birth rate: births to mothers ages 15 to 19 per 1,000 females ages 15 to 19, 3 year average",
    "unit": "rate per 1,000", "period": period, "values": vals,
    "california": ca_rate, "california_source": "published", "higher_is_worse": True,
    "note": (f"Published age-specific birth rate from the {edition}, births to adolescent mothers ages 15 to 19 by county of "
             f"residence, based on the average annual number of births {period} and the {popyr} female population ages 15 to 19."
             f"{flag}{sflag}{mflag} California value is the statewide rate published in the same CDPH table." + tnote),
    "source_url": src,
    "trend": tr}]})

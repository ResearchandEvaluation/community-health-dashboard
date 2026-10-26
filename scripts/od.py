"""od: drug overdose death rate, published values from the CDPH County Health Status Profiles
(data.chhs.ca.gov dataset county-health-status-profiles), Table 19.
Uses the published age-adjusted death rate per 100,000 (based on the 3-year average number of deaths) for each
county and CALIFORNIA, newest edition, plus a trend across editions that publish the same indicator.
The 2021 and 2022 editions published Table 19 as 'Drug Induced Deaths' (a broader definition); the 2023 edition
onward publishes 'Drug Overdose Deaths'. The trend uses only editions with the newest edition's indicator.
No values are calculated by PHIL. Previous source (NCHS VSRR provisional counts) is kept in od_vsrr_old.py."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chhs_common import write, COUNTIES
from chsp_common import newest_edition, editions, indicator_rows, published, trend, sql

pub, rid, src = newest_edition()
tab = sql(f'SELECT DISTINCT "Table","Health_Indicator_Desc" FROM "{rid}" '
          "WHERE \"Health_Indicator_Desc\" ILIKE '%drug%'")
assert len(tab) == 1, tab
DESC = tab[0]["Health_Indicator_Desc"]          # 'Drug Overdose Deaths' in the 2023 to 2025 editions
r = indicator_rows(rid, DESC)
ca = r["California"]
assert ca["Age-Adjusted_Rate_Label"] == "Age-Adjusted Death Rate" and ca["Rate_Multiplier"] == "100000"
yrs = ca["Numerator_Year_Period"]
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

# Editions that publish this table under a different indicator name (definition break), for the note.
other = []
for p, erid in editions():
    if p in used:
        continue
    t = sql(f'SELECT DISTINCT "Health_Indicator_Desc" FROM "{erid}" WHERE "Health_Indicator_Desc" ILIKE \'%drug%\'')
    if t:
        other.append((p, t[0]["Health_Indicator_Desc"]))

edition = f"California Department of Public Health (CDPH) County Health Status Profiles {pub}"
flag = (f" CDPH flags the rate as unreliable (relative standard error of 23 percent or more) for {', '.join(unreliable)}."
        if unreliable else "")
sflag = f" CDPH suppressed the value for {', '.join(supp)}." if supp else ""
missing = [c for c in COUNTIES if rate[c] is None]
mflag = f" No value is published for {', '.join(missing)}." if missing else ""
older = "; ".join(f"{p}: {', '.join(cs)}" for p, cs in unrel.items() if p != period and p in tr["periods"])
brk = ""
if other:
    names = sorted({d for _, d in other})
    brk = (f" Earlier editions ({', '.join(str(p) for p, _ in other)}) published this table as "
           f"{' and '.join(repr(n).replace(chr(39), '') for n in names)}, a different definition, so those periods are left out of the trend.")
tnote = (f" Trend shows the same published rate from the {used[0]} to {used[-1]} editions, covering the periods {tr['periods'][0]} through {period}; "
         "each edition covers a 3 year period, so adjacent periods share 2 years of deaths, and each edition uses the "
         "population estimates current when it was published." + brk
         + (f" Rates flagged unreliable in earlier periods: {older}." if older else ""))

write("od", {"key": "od", "measures": [{
    "id": f"od_rate_aa_{yrs.replace('-', '_')}",
    "label": "Drug overdose deaths, age-adjusted rate per 100,000 (3-year average)",
    "unit": "rate per 100,000", "period": period, "values": rate,
    "california": ca_rate, "california_source": "published", "higher_is_worse": True,
    "note": (f"Published age-adjusted death rate from the {edition}, drug overdose deaths by county of residence, "
             f"based on the average annual number of deaths {period} and {popyr} population.{flag}{sflag}{mflag} "
             "California value is the statewide rate published in the same CDPH table." + tnote),
    "source_url": src,
    "trend": tr}]})

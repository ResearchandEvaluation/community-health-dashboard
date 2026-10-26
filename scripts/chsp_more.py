"""Eight indicators from the CDPH County Health Status Profiles (data.chhs.ca.gov dataset
county-health-status-profiles), newest edition, with a trend across all published editions.
Uses the published age-adjusted rate where the table publishes one (death tables), otherwise the
published Rate/Percentage (infant mortality, low birthweight, prenatal care). Also records the
Healthy People 2030 objective number and target as published in the same rows. One output file per
key. No values are calculated by PHIL."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chhs_common import write, COUNTIES
from chsp_common import newest_edition, indicator_rows, published, trend, num

AA = ("Age-Adjusted_Rate", "Age-Adjusted_Rate_Label", "Age-Adjusted Death Rate", "100000")

# key: (Health_Indicator_Desc, value column, label column, expected label, multiplier, unit,
#       higher_is_worse, measure id stem, measure label, event wording)
MEASURES = {
    "chdmort": ("Deaths Due to Coronary Heart Disease", *AA, "rate per 100,000", True,
                "chd_death_rate_aa", "Coronary heart disease death rate, age adjusted, 3 year average",
                "deaths due to coronary heart disease"),
    "diabmort": ("Deaths Due to Diabetes", *AA, "rate per 100,000", True,
                 "diabetes_death_rate_aa", "Diabetes death rate, age adjusted, 3 year average",
                 "deaths due to diabetes"),
    "infmort": ("Infant Mortality, All Race/Ethnic Groups", "Rate/Percentage", "Rate/Percentage_Label",
                "Birth Cohort Infant Death Rate", "1000", "rate per 1,000", True,
                "infant_mortality_rate", "Infant deaths per 1,000 live births, all race and ethnic groups, 3 year birth cohort",
                "infant deaths (deaths before age 1 year) among live births"),
    "lbw": ("Low Birthweight Infants", "Rate/Percentage", "Rate/Percentage_Label",
            "Low Birthweight Percent", "100", "percent", True,
            "low_birthweight_pct", "Low birthweight infants (under 2,500 grams) as a percent of live births, 3 year average",
            "live births with low birthweight (under 2,500 grams)"),
    "prenatal": ("Prenatal Care Begun during the First Trimester of Pregnancy", "Rate/Percentage",
                 "Rate/Percentage_Label", "First Trimester Prenatal Care Percent", "100", "percent", False,
                 "prenatal_first_trimester_pct",
                 "Live births with prenatal care begun in the first trimester, percent of live births, 3 year average",
                 "live births to mothers whose prenatal care began in the first trimester of pregnancy"),
    "firearm": ("Firearm Related Deaths", *AA, "rate per 100,000", True,
                "firearm_death_rate_aa", "Firearm related death rate, age adjusted, 3 year average",
                "firearm related deaths (all intents)"),
    "homicide": ("Deaths Due to Homicide", *AA, "rate per 100,000", True,
                 "homicide_death_rate_aa", "Homicide death rate, age adjusted, 3 year average",
                 "deaths due to homicide"),
    "mvc": ("Deaths Due to Motor Vehicle Traffic Crashes", *AA, "rate per 100,000", True,
            "mvc_death_rate_aa", "Motor vehicle traffic crash death rate, age adjusted, 3 year average",
            "deaths due to motor vehicle traffic crashes"),
}

pub, rid, src = newest_edition()
edition = f"California Department of Public Health (CDPH) County Health Status Profiles {pub}"

for key, (desc, col, lab_col, lab, mult, unit, worse, stem, label, event) in MEASURES.items():
    r = indicator_rows(rid, desc)
    assert r is not None, (key, desc)
    ca = r["California"]
    assert ca[lab_col] == lab and ca["Rate_Multiplier"] == mult, (key, ca[lab_col], ca["Rate_Multiplier"])
    yrs = ca["Numerator_Year_Period"]          # e.g. 2021-2023
    period = yrs.replace("-", " to ")
    denyr = ca["Denominator_Year_Period"]
    denlab = ca["Denominator_Label"]

    # Healthy People objective, as published in the same rows (identical across the table)
    hp = {(row.get("Healthy_People_Decade"), row.get("Healthy_People_Objective_Number"),
           row.get("Healthy_People_Objective_Target")) for row in r.values()}
    assert len(hp) == 1, (key, hp)
    hp_decade, hp_objective, hp_target_text = hp.pop()
    hp_target = num(hp_target_text)
    hp_objective = hp_objective or None

    vals, unreliable, supp = {}, [], []
    for c in COUNTIES:
        row = r.get(c)
        assert row is None or row["Numerator_Year_Period"] == yrs
        v, code = published(row, col)
        vals[c] = v
        if code == "4" and isinstance(v, float):
            unreliable.append(c)
        if v == "suppressed":
            supp.append(c)
    ca_val, _ = published(ca, col)
    assert isinstance(ca_val, float), (key, ca_val)

    tr, used, unrel = trend(desc, col, lab_col, lab, mult)
    assert tr["periods"][-1] == period and used[-1] == pub
    assert [tr["values"][c][-1] for c in COUNTIES] == [vals[c] for c in COUNTIES]
    assert tr["california"][-1] == ca_val

    if col == "Age-Adjusted_Rate":
        what = (f"Published age-adjusted death rate per 100,000 population from the {edition}, {event} by county of "
                f"residence, based on the average annual number of deaths {period} and {denyr} population.")
        flagword = "rate"
    elif unit == "percent":
        what = (f"Published percent from the {edition}, {event}, by county of residence, "
                f"based on the total live births {period}.")
        flagword = "percent"
    else:
        what = (f"Published birth cohort infant death rate per 1,000 live births from the {edition}, {event}, "
                f"by county of residence, based on the total live births {period} and the infant deaths among them.")
        flagword = "rate"
    flag = (f" CDPH flags the {flagword} as unreliable (relative standard error of 23 percent or more) for "
            f"{', '.join(unreliable)}." if unreliable else "")
    sflag = f" CDPH suppressed the value for {', '.join(supp)}." if supp else ""
    missing = [c for c in COUNTIES if vals[c] is None]
    mflag = f" No value is published for {', '.join(missing)}." if missing else ""
    if hp_target is not None:
        hpnote = (f" Healthy People {hp_decade} objective {hp_objective} target as published in the same table: "
                  f"{hp_target_text}.")
    else:
        hpnote = f" CDPH publishes no Healthy People {hp_decade} objective target for this indicator."
    older = "; ".join(f"{p}: {', '.join(cs)}" for p, cs in unrel.items() if p != period and p in tr["periods"])
    tnote = (f" Trend shows the same published {flagword} from the {used[0]} to {used[-1]} editions, covering the periods "
             f"{tr['periods'][0]} through {period}; each edition covers a 3 year period, so adjacent periods share 2 years of "
             f"{denlab.lower() if unit != 'rate per 100,000' else 'deaths'}"
             + (", and each edition uses the population estimates current when it was published." if col == "Age-Adjusted_Rate" else ".")
             + (f" Values flagged unreliable in earlier periods: {older}." if older else ""))

    measure = {
        "id": f"{stem}_{yrs.replace('-', '_')}",
        "label": label,
        "unit": unit, "period": period, "values": vals,
        "california": ca_val, "california_source": "published", "higher_is_worse": worse,
        "hp_target": hp_target, "hp_objective": hp_objective,
        "note": what + flag + sflag + mflag + " California value is the statewide value published in the same CDPH table."
                + hpnote + tnote,
        "source_url": src,
        "trend": tr,
    }
    write(key, {"key": key, "measures": [measure]})

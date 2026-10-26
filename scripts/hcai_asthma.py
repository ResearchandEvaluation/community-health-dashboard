"""Pull age-adjusted asthma emergency department (ED) visit rates by county for the PHIL dashboard.

Writes data/out/asthmaED.json.
Source: data.chhs.ca.gov dataset 'asthma-emergency-department-visit-rates' (California Department of Public
Health, California Breathing Asthma Program, from Department of Health Care Access and Information ED data),
resource "Asthma ED Visit Rates by County 2015-Present" (94d84508-8046-40a7-b8d9-0ed73b13b697).
Measures: age-adjusted ED visit rate per 10,000 residents, all ages (STRATA = 'Total population') and
children 0 to 17 years (STRATA = 'Child vs. adult', AGE GROUP = '0-17 years'). Newest year plus a trend from
2016 onward (the publisher advises against comparing 2015 ICD-9-CM data with 2016 and later ICD-10-CM data).
The Let's Get Healthy California indicator 07 dataset holds the same measure but stops at 2019, so the
main dataset is used.
"""
from chhs_common import sql, inlist, COUNTIES, write

RES = "94d84508-8046-40a7-b8d9-0ed73b13b697"
SRC = "https://data.chhs.ca.gov/dataset/asthma-emergency-department-visit-rates/resource/" + RES
TREND_START = 2016
SUPPRESSED = "Count and rate suppressed in accordance with data de-identification guidelines"
UNSTABLE = "Rate not available due to statistical instability"


def value(row):
    v = row["AGE-ADJUSTED ED VISIT RATE"]
    c = row["COMMENT"] or ""
    if v not in (None, ""):
        return float(v)
    if c.startswith("Count and rate suppressed"):
        return "suppressed"
    return None


def main():
    rows = sql(f'SELECT "COUNTY","YEAR","STRATA","AGE GROUP","AGE-ADJUSTED ED VISIT RATE","COMMENT" '
               f'FROM "{RES}" WHERE "COUNTY" IN ({inlist(COUNTIES + ["California"])}) '
               f"AND \"STRATA\" IN ('Total population','Child vs. adult')")
    years = sorted({int(r["YEAR"]) for r in rows})
    newest = years[-1]
    trend_years = [y for y in years if y >= TREND_START]

    # (strata, age group) -> {county: {year: value}}
    table = {}
    flags = {}
    for r in rows:
        key = (r["STRATA"], r["AGE GROUP"])
        table.setdefault(key, {}).setdefault(r["COUNTY"], {})[int(r["YEAR"])] = value(r)
        if r["COMMENT"] and int(r["YEAR"]) >= TREND_START:
            flags.setdefault(key, []).append(f"{r['COUNTY']} {r['YEAR']}: {r['COMMENT']}")

    def measure(key, mid, label, extra):
        t = table[key]
        vals = {c: t.get(c, {}).get(newest) for c in COUNTIES}
        flag_txt = ""
        mine = sorted(flags.get(key, []))
        if mine:
            flag_txt = " Publisher comments on cells in this measure: " + "; ".join(mine) + "."
        return {
            "id": mid,
            "label": label,
            "unit": "rate per 10,000",
            "period": str(newest),
            "values": vals,
            "california": t["California"].get(newest),
            "california_source": "published",
            "higher_is_worse": True,
            "note": ("Published by the California Department of Public Health (CDPH) California Breathing Asthma "
                     "Program from Department of Health Care Access and Information (HCAI) emergency department "
                     f"records, calendar years {trend_years[0]} to {newest}. Rates are age-adjusted per 10,000 "
                     "residents and count visits with a primary diagnosis of asthma, so one person with several "
                     "visits is counted each time. " + extra +
                     " Suppressed cells are withheld by the publisher under data de-identification guidelines; "
                     "cells the publisher marks as statistically unstable are shown as null." + flag_txt),
            "source_url": SRC,
            "trend": {
                "periods": [str(y) for y in trend_years],
                "values": {c: [t.get(c, {}).get(y) for y in trend_years] for c in COUNTIES},
                "california": [t["California"].get(y) for y in trend_years],
            },
        }

    measures = [
        measure(("Total population", "All ages"), "asthma_ed_rate_all_ages",
                "Asthma emergency department visits, all ages, age-adjusted rate per 10,000 residents",
                "The 2015 rate is left out of the trend because asthma coding changed from ICD-9-CM to "
                "ICD-10-CM on October 1, 2015 and CDPH advises against comparing across that change."),
        measure(("Child vs. adult", "0–17 years"), "asthma_ed_rate_children",
                "Asthma emergency department visits among children ages 0 to 17, age-adjusted rate per 10,000 "
                "residents",
                "The 2015 rate is left out of the trend because asthma coding changed from ICD-9-CM to "
                "ICD-10-CM on October 1, 2015 and CDPH advises against comparing across that change."),
    ]
    write("asthmaED", {"key": "asthmaED", "measures": measures, "geo_note": ""})


if __name__ == "__main__":
    main()

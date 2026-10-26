"""Pull certified WIC participants by county and WIC category for the PHIL dashboard.

Writes data/out/wic.json.
Source: data.chhs.ca.gov dataset 'cdph-wic-participants-by-county' (California Department of Public Health,
Women, Infants and Children Program), resource "WIC Participants by County of Residence and by WIC Category,
2019 Onwards" (d17babd7-815e-4bad-a1a9-55b70540e944).

The resource publishes one row per county, period, and WIC category (Prenatal, Breastfeeding, Non-Breastfeeding,
Infant, Child Aged 1, 2, 3, 4). It publishes no all-category total row for a county or for the state, so each
category is written as its own measure and no total is computed. The 'Statewide' rows give the California
value for each category. Periods are YYYYMM (month) or YYYY (annual row, meaning undocumented in the dataset);
the newest month is used, and the trend uses the same calendar month in each earlier year.
Suppressed cells (fewer than 11 participants) are published as '.'.
"""
from chhs_common import sql, inlist, COUNTIES, write

RES = "d17babd7-815e-4bad-a1a9-55b70540e944"
SRC = "https://data.chhs.ca.gov/dataset/cdph-wic-participants-by-county/resource/" + RES
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]
CATEGORIES = [
    ("Prenatal", "wic_prenatal", "Pregnant WIC participants (Prenatal category), certified"),
    ("Breastfeeding", "wic_breastfeeding", "Postpartum breastfeeding WIC participants, certified"),
    ("Non-Breastfeeding", "wic_non_breastfeeding", "Postpartum non-breastfeeding WIC participants, certified"),
    ("Infant", "wic_infant", "Infant WIC participants under age 1, certified"),
    ("Child Aged 1", "wic_child_1", "WIC participants aged 1, certified"),
    ("Child Aged 2", "wic_child_2", "WIC participants aged 2, certified"),
    ("Child Aged 3", "wic_child_3", "WIC participants aged 3, certified"),
    ("Child Aged 4", "wic_child_4", "WIC participants aged 4, certified"),
]


def num(v):
    if v is None or v.strip() in ("", "."):
        return "suppressed" if v is not None and v.strip() == "." else None
    return int(v.replace(",", ""))


def label_period(ym):
    return f"{MONTHS[int(ym[4:6]) - 1]} {ym[:4]}"


def main():
    periods = [r["p"] for r in sql(f'SELECT DISTINCT "YEAR MONTH" AS p FROM "{RES}"')]
    months = sorted(p for p in periods if len(p) == 6)
    newest = months[-1]
    trend_months = sorted(p for p in months if p[4:6] == newest[4:6])
    rows = sql(f'SELECT "COUNTY OF RESIDENCE" AS c, "YEAR MONTH" AS p, "CATEGORY" AS cat, '
               f'"NUMBER OF CERTIFIED PARTICIPANTS" AS n FROM "{RES}" '
               f'WHERE "YEAR MONTH" IN ({inlist(trend_months)}) '
               f'AND "COUNTY OF RESIDENCE" IN ({inlist(COUNTIES + ["Statewide"])})')
    table = {}
    for r in rows:
        table.setdefault(r["cat"], {}).setdefault(r["c"], {})[r["p"]] = num(r["n"])

    measures = []
    for cat, mid, label in CATEGORIES:
        t = table[cat]
        vals = {c: t.get(c, {}).get(newest) for c in COUNTIES}
        n_supp = sum(1 for v in vals.values() if v == "suppressed")
        measures.append({
            "id": mid,
            "label": label,
            "unit": "count",
            "period": label_period(newest),
            "values": vals,
            "california": t.get("Statewide", {}).get(newest),
            "california_source": "published",
            "higher_is_worse": None,
            "note": ("Published by the California Department of Public Health (CDPH) Women, Infants and Children "
                     f"(WIC) Program for the month of {label_period(newest)}; certified participants are people "
                     "who completed eligibility and enrollment and were approved for benefits in that month. The "
                     "dataset publishes one row per WIC category and no all-category total for a county or the "
                     "state, so this measure covers the " + cat + " category only. California is the "
                     "publisher's Statewide row. Cells with fewer than 11 participants are suppressed by CDPH" +
                     (f" ({n_supp} of the 17 counties in this month)." if n_supp else ".") +
                     f" Trend shows {MONTHS[int(newest[4:6]) - 1]} of each year from {trend_months[0][:4]} to "
                     f"{newest[:4]}."),
            "source_url": SRC,
            "trend": {
                "periods": [label_period(p) for p in trend_months],
                "values": {c: [t.get(c, {}).get(p) for p in trend_months] for c in COUNTIES},
                "california": [t.get("Statewide", {}).get(p) for p in trend_months],
            },
        })
    write("wic", {"key": "wic", "measures": measures, "geo_note": ""})
    print("wic", label_period(newest))


if __name__ == "__main__":
    main()

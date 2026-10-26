"""Pull ACS 5-year Medicaid/means-tested public coverage percents (medical, medicalKids).

Usage: CENSUS_API_KEY=<key> python3 acs_medicaid.py [vintage]
Source: U.S. Census Bureau American Community Survey (ACS) 5-year subject table S2704,
Public Health Insurance Coverage by Type and Selected Characteristics.
Variables (Percent Public Coverage column, published by the Census Bureau):
  S2704_C03_006E  Medicaid/means-tested public coverage alone or in combination, all ages
  S2704_C03_007E  Medicaid/means-tested public coverage alone or in combination, under 19
Counties and California come from the same table. Reuses helpers from acs.py.
"""
import os
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acs  # noqa: E402
from acs import COUNTIES, latest_vintage, get, subject_measure, measure  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "out")


def write(key, m):
    with open(f"{OUT}/{key}.json", "w") as f:
        json.dump({"key": key, "measures": [m]}, f, indent=2)
    print("wrote", key)


def main():
    v = latest_vintage()
    period = f"{v - 4} to {v}"
    sub = f"https://api.census.gov/data/{v}/acs/acs5/subject"
    url = f"{sub}?get=NAME,S2704_C03_006E,S2704_C03_006M,S2704_C03_007E,S2704_C03_007M&for=county:*&in=state:06"
    if not acs.KEY:
        raise SystemExit("Set the CENSUS_API_KEY environment variable.")
    d = get(sub, ["S2704_C03_006E", "S2704_C03_006M", "S2704_C03_007E", "S2704_C03_007M"])
    base = ("American Community Survey (ACS) 5-year estimates, table S2704. Medicaid/means-tested public coverage "
            "includes Medi-Cal and other means-tested public health coverage, alone or in combination with other "
            "coverage, as reported by survey respondents.")
    m = subject_measure(d, "S2704_C03_006E", "S2704_C03_006M", "medicaid_pct_all",
                        "People with Medicaid or other means-tested public health coverage, all ages "
                        "(civilian noninstitutionalized population)", period, url, base)
    m["higher_is_worse"] = None
    write("medical", m)
    k = subject_measure(d, "S2704_C03_007E", "S2704_C03_007M", "medicaid_pct_under19",
                        "Children and youth under age 19 with Medicaid or other means-tested public health coverage "
                        "(civilian noninstitutionalized population)", period, url,
                        base + " The Census Bureau publishes this measure for the under 19 age group.")
    k["higher_is_worse"] = None
    write("medicalKids", k)


if __name__ == "__main__":
    main()

"""Pull ACS 5-year housing cost, vehicle, broadband, disability, and language indicators.

Usage: CENSUS_API_KEY=<key> python3 acs_more.py [vintage]
Source: U.S. Census Bureau American Community Survey (ACS) 5-year estimates, newest vintage.
Every value is a percent the Census Bureau publishes directly (subject or data profile tables);
nothing is calculated here. Counties and California come from the same table for each measure.

Keys and variables:
  acsHousing
    DP04_0142PE     Occupied units paying rent with gross rent 35.0 percent or more of household
                    income (data profile DP04). DP04 publishes rent burden as two bands (30.0 to 34.9
                    and 35.0 percent or more) and no single 30 percent or more percent. Subject table
                    S0102 (Total column, S0102_C01_105E) publishes a 30 percent or more renter percent
                    but it is null for Colusa, Glenn, and Trinity, so the DP04 band is used and labeled
                    exactly.
    DP04_0115PE     Owner-occupied housing units with a mortgage with selected monthly owner costs
                    35.0 percent or more of household income (DP04). No single 30 percent or more
                    percent is published for owners with a mortgage, so the published 35.0 percent
                    or more band is used and labeled exactly.
  acsVehicle     DP04_0058PE   Occupied housing units with no vehicles available
  acsBroadband   S2801_C02_014E  Households with a broadband Internet subscription of any type
  acsDisability  S1810_C03_001E  Percent with a disability, civilian noninstitutionalized population
  acsLanguage    S1601_C06_001E  Percent of population 5 years and over who speak English less than "very well"
Reuses helpers from acs.py (get, subject_measure, coefficient of variation flags).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acs  # noqa: E402
from acs import latest_vintage, get, subject_measure  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "out")


def write(key, measures):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"{key}.json"), "w") as f:
        json.dump({"key": key, "measures": measures, "geo_note": ""}, f, indent=2)
    print("wrote", key)


def pull(base, est, moe, mid, label, period, url, note, hiw):
    d = get(base, [est, moe])
    m = subject_measure(d, est, moe, mid, label, period, url, note)
    m["higher_is_worse"] = hiw
    return m


def main():
    v = latest_vintage()
    period = f"{v - 4} to {v}"
    sub = f"https://api.census.gov/data/{v}/acs/acs5/subject"
    prof = f"https://api.census.gov/data/{v}/acs/acs5/profile"
    if not acs.KEY:
        raise SystemExit("Set the CENSUS_API_KEY environment variable.")
    src = "American Community Survey (ACS) 5-year estimates"

    # acsHousing
    rent_url = f"{prof}?get=NAME,DP04_0142PE,DP04_0142PM&for=county:*&in=state:06"
    rent = pull(prof, "DP04_0142PE", "DP04_0142PM", "rent_35pct_or_more",
                "Renter households paying 35.0 percent or more of household income on gross rent",
                period, rent_url,
                f"{src}, data profile DP04. Percent of occupied units paying rent (excluding units where the "
                "ratio cannot be computed) whose gross rent is 35.0 percent or more of household income. The "
                "Census Bureau publishes rent burden in bands and does not publish a single 30 percent or more "
                "percent in this table, so the published 35.0 percent or more band is shown.", True)
    own_url = f"{prof}?get=NAME,DP04_0115PE,DP04_0115PM&for=county:*&in=state:06"
    own = pull(prof, "DP04_0115PE", "DP04_0115PM", "owner_mortgage_35pct_or_more",
               "Owner households with a mortgage paying 35.0 percent or more of household income on "
               "selected monthly owner costs",
               period, own_url,
               f"{src}, data profile DP04. Percent of owner-occupied housing units with a mortgage (excluding "
               "units where the ratio cannot be computed) whose selected monthly owner costs are 35.0 percent or "
               "more of household income. The Census Bureau publishes owner cost burden in bands and does not "
               "publish a single 30 percent or more percent for units with a mortgage, so the published 35.0 "
               "percent or more band is shown.", True)
    write("acsHousing", [rent, own])

    # acsVehicle
    veh_url = f"{prof}?get=NAME,DP04_0058PE,DP04_0058PM&for=county:*&in=state:06"
    veh = pull(prof, "DP04_0058PE", "DP04_0058PM", "no_vehicle",
               "Households with no vehicle available", period, veh_url,
               f"{src}, data profile DP04. Percent of occupied housing units with no vehicles available, "
               "as published.", True)
    write("acsVehicle", [veh])

    # acsBroadband
    bb_url = f"{sub}?get=NAME,S2801_C02_014E,S2801_C02_014M&for=county:*&in=state:06"
    bb = pull(sub, "S2801_C02_014E", "S2801_C02_014M", "broadband",
              "Households with a broadband Internet subscription", period, bb_url,
              f"{src}, subject table S2801. Percent of total households with an Internet subscription that is "
              "broadband of any type (cellular data plan, cable, fiber optic, DSL, or satellite), as published.",
              False)
    write("acsBroadband", [bb])

    # acsDisability
    dis_url = f"{sub}?get=NAME,S1810_C03_001E,S1810_C03_001M&for=county:*&in=state:06"
    dis = pull(sub, "S1810_C03_001E", "S1810_C03_001M", "disability",
               "People with a disability (civilian noninstitutionalized population)", period, dis_url,
               f"{src}, subject table S1810. Percent of the total civilian noninstitutionalized population with "
               "a disability, as published.", None)
    write("acsDisability", [dis])

    # acsLanguage
    lang_url = f"{sub}?get=NAME,S1601_C06_001E,S1601_C06_001M&for=county:*&in=state:06"
    lang = pull(sub, "S1601_C06_001E", "S1601_C06_001M", "limited_english",
                "People age 5 and older who speak English less than very well", period, lang_url,
                f"{src}, subject table S1601. Percent of the population 5 years and over who speak English less "
                "than \"very well\", as published.", None)
    write("acsLanguage", [lang])
    print("done", v)


if __name__ == "__main__":
    main()

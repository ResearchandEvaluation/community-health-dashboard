"""Pull HRSA Health Professional Shortage Area (HPSA) indicators (hpsaPC, hpsaMH).

Downloads the HRSA Data Warehouse HPSA detail files, keeps rows with HPSA Status
'Designated', and for each county counts distinct HPSA IDs with at least one component
row in that county (all designation types: geographic, high needs geographic, population,
and facility) and reports the highest HPSA score among them.
"""
import os
import io, json, urllib.request
import pandas as pd

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "out")
COUNTIES = {
    "Butte": "06007", "Colusa": "06011", "Del Norte": "06015", "Glenn": "06021", "Humboldt": "06023",
    "Lake": "06033", "Mendocino": "06045", "Shasta": "06089", "Tehama": "06103", "Trinity": "06105",
    "Siskiyou": "06093", "Los Angeles": "06037", "San Bernardino": "06071", "Sonoma": "06097",
    "Marin": "06041", "Sutter": "06101", "Napa": "06055",
}
FILES = {
    "hpsaPC": ("https://data.hrsa.gov/DataDownload/DD_Files/BCD_HPSA_FCT_DET_PC.csv", "primary care"),
    "hpsaMH": ("https://data.hrsa.gov/DataDownload/DD_Files/BCD_HPSA_FCT_DET_MH.csv", "mental health"),
}


def run(key, url, disc):
    with urllib.request.urlopen(url) as r:
        d = pd.read_csv(io.BytesIO(r.read()), dtype=str, low_memory=False)
    d = d[(d["HPSA Status"] == "Designated") & (d["Primary State Abbreviation"] == "CA")].copy()
    d["score"] = pd.to_numeric(d["HPSA Score"], errors="coerce")
    upd = pd.to_datetime(d["HPSA Designation Last Update Date"], errors="coerce").max()
    as_of = f"Designations as of {upd:%B} {upd.day}, {upd:%Y}" if pd.notna(upd) else "Current designations"
    fips = d["Common State County FIPS Code"]
    counts, scores, types = {}, {}, {}
    for name, f in COUNTIES.items():
        sub = d[fips == f].drop_duplicates("HPSA ID")
        counts[name] = int(sub["HPSA ID"].nunique())
        scores[name] = int(sub["score"].max()) if len(sub) else 0
        types[name] = sub["Designation Type"].value_counts().to_dict()
    ca_count = int(d["HPSA ID"].nunique())
    multi = d.groupby("HPSA ID")["Common State County FIPS Code"].nunique()
    multi_n = int((multi > 1).sum())
    whole = sorted(n for n, f in COUNTIES.items()
                   if ((fips == f) & (d["HPSA Component Type Description"] == "Single County")
                       & d["Designation Type"].isin(["Geographic HPSA", "High Needs Geographic HPSA", "HPSA Population"])).any())
    count_note = (f"Counts distinct Health Professional Shortage Area (HPSA) identification numbers with status Designated that have at least one component in the county, "
                  f"including geographic, high needs geographic, population, and facility designations (Federally Qualified Health Centers, "
                  f"Rural Health Clinics, Indian Health Service, Tribal, and Urban Indian health organizations, correctional and other facilities). "
                  f"HPSAs with status Proposed for Withdrawal are excluded. The California value is the statewide count of distinct designated "
                  f"{disc} HPSAs")
    count_note += (f"; {multi_n} HPSA{' spans' if multi_n == 1 else 's span'} more than one county and {'is' if multi_n == 1 else 'are'} counted in each county covered." if multi_n else ".")
    if whole:
        count_note += (" Counties with a whole-county geographic or population designation: " + ", ".join(whole) + ".")
    else:
        count_note += " None of the 17 counties has a whole-county geographic or population designation; all geographic and population designations cover parts of counties (census tracts or county subdivisions)."
    score_note = (f"Highest HPSA score among designated {disc} HPSAs in the county (scale 0 to 25 for {disc}"
                  f", higher means greater shortage). A value of 0 means the county has no designated "
                  f"{disc} HPSA. No statewide score is published.")
    zero = [n for n in COUNTIES if counts[n] == 0]
    if zero:
        score_note += " Counties with no designated HPSA: " + ", ".join(zero) + "."
    period = as_of
    out = {"key": key, "measures": [
        {"id": f"{key.lower()}_count", "label": f"Designated {disc} Health Professional Shortage Areas (HPSAs) in county",
         "unit": "count", "period": period, "values": counts, "california": ca_count, "california_source": "calculated",
         "higher_is_worse": True, "note": count_note, "source_url": url},
        {"id": f"{key.lower()}_max_score", "label": f"Highest {disc} HPSA score in county",
         "unit": "score (0 to 25, higher means greater shortage)", "period": period, "values": scores, "california": None,
         "california_source": "published", "higher_is_worse": True, "note": score_note, "source_url": url},
    ], "geo_note": ""}
    with open(f"{OUT}/{key}.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print(key, counts, scores, ca_count, whole, multi_n)
    for n in COUNTIES:
        print("  ", n, types[n])


if __name__ == "__main__":
    for k, (u, disc) in FILES.items():
        run(k, u, disc)

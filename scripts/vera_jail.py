"""jailRate: jail population rate by county, Vera Institute of Justice Incarceration Trends (version 3 and later).
Source files: https://github.com/vera-institute/incarceration-trends (incarceration_trends_county.csv and
incarceration_trends_state.csv). Vera publishes total_jail_pop_rate: people in jail per 100,000 residents ages 15 to 64.
Published Vera rates only; the newest year with a California county rate is shown, with a trend."""
import csv, io, json, os, time, requests

RAW = "https://raw.githubusercontent.com/vera-institute/incarceration-trends/main/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "out")
COUNTIES = ["Butte", "Colusa", "Del Norte", "Glenn", "Humboldt", "Lake", "Mendocino", "Shasta", "Tehama", "Trinity",
            "Siskiyou", "Los Angeles", "San Bernardino", "Sonoma", "Marin", "Sutter", "Napa"]


def get(name):
    for i in range(4):
        try:
            r = requests.get(RAW + name, timeout=300); r.raise_for_status(); return r.text
        except requests.exceptions.RequestException:
            if i == 3: raise
            time.sleep(15 * (i + 1))


def num(v):
    try: return float(v)
    except (TypeError, ValueError): return None


def main():
    county = {}
    for r in csv.DictReader(io.StringIO(get("incarceration_trends_county.csv"))):
        if r["state_abbr"] == "CA" and num(r["total_jail_pop_rate"]) is not None:
            county.setdefault(r["year"], {})[r["county_name"].replace(" County", "")] = num(r["total_jail_pop_rate"])
    state = {r["year"]: num(r["total_jail_pop_rate"]) for r in csv.DictReader(io.StringIO(get("incarceration_trends_state.csv")))
             if r.get("state_abbr") == "CA" and num(r.get("total_jail_pop_rate")) is not None}
    years = sorted(y for y in county if len(county[y]) >= 40)
    newest = years[-1]
    trend = years[-8:]
    m = {"id": "jail_rate", "label": "People in jail per 100,000 residents ages 15 to 64", "unit": "rate per 100,000",
         "period": newest, "values": {c: county[newest].get(c) for c in COUNTIES}, "california": state.get(newest),
         "california_source": "published", "higher_is_worse": True,
         "note": ("Average daily jail population per 100,000 residents ages 15 to 64, as published by the Vera Institute "
                  "of Justice from Bureau of Justice Statistics and state and local jail data."),
         "source_url": "https://github.com/vera-institute/incarceration-trends",
         "all_ca_counties": county[newest],
         "trend": {"periods": trend, "values": {c: [county[y].get(c) for y in trend] for c in COUNTIES},
                   "california": [state.get(y) for y in trend]}}
    json.dump({"key": "jailRate", "measures": [m]}, open(os.path.join(OUT, "jailRate.json"), "w"), indent=1)
    print("wrote jailRate", newest, m["values"]["Lake"], m["california"])


if __name__ == "__main__":
    main()

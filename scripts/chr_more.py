"""Additional County Health Rankings & Roadmaps (CHR&R) measures, University of Wisconsin Population Health Institute.
Same national analytic data CSV as chr_providers.py (newest release found on the CHR&R data documentation page).
Published CHR&R values only, with the published California value from the same file. Proportions are shown as
percents (the published value times 100); no other calculation is done.

Writes one file per dashboard card:
  chrFood      food environment index, limited access to healthy foods
  chrActive    access to exercise opportunities
  chrLunch     children eligible for free or reduced-price lunch
  chrPrevent   flu vaccinations, mammography screening (Medicare enrollees)
  chrDentists  residents per dentist
  chrJobs      unemployment
  chrAir       air pollution, fine particulate matter
  chrReading   reading scores, grades 3 to 8
  chrChildMort child mortality
"""
import csv, io, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chr_providers import get, DOC, SITE, OUT, COUNTIES

PUB = "Published by County Health Rankings & Roadmaps (University of Wisconsin Population Health Institute) in its annual national data file. "
# key -> list of (measure id, CSV column, label, unit, kind, higher_is_worse, note)
# kind: "pct" (proportion shown as percent), "num" (as published), "ratio" (population per provider, rounded)
FILES = {
    "chrFood": [
        ("chr_food_env", "Food Environment Index raw value", "Food environment index (0 is worst, 10 is best)", "score out of 10", "num", False,
         "An index of factors that contribute to a healthy food environment, combining limited access to healthy foods and food insecurity. CHR&R source: USDA Food Environment Atlas and Feeding America Map the Meal Gap."),
        ("chr_food_access", "Limited Access to Healthy Foods raw value", "People who are low income and live far from a grocery store", "percent", "pct", True,
         "CHR&R source: USDA Food Environment Atlas. Low income means a household income at or below 200 percent of the federal poverty level; far means more than 10 miles from a grocery store in rural areas and more than 1 mile in urban areas."),
    ],
    "chrActive": [
        ("chr_exercise_access", "Access to Exercise Opportunities raw value", "People who live close to a park or recreational facility", "percent", "pct", False,
         "CHR&R source: Business Analyst, Delorme map data, ESRI, and U.S. Census files. Close means within half a mile of a park, 1 mile of a recreational facility in urban areas, or 3 miles in rural areas."),
    ],
    "chrLunch": [
        ("chr_frpl", "Children Eligible for Free or Reduced Price Lunch raw value", "Children enrolled in public schools who are eligible for free or reduced-price lunch", "percent", "pct", True,
         "CHR&R source: National Center for Education Statistics. Eligibility is based on household income at or below 185 percent of the federal poverty level."),
    ],
    "chrPrevent": [
        ("chr_flu", "Flu Vaccinations raw value", "Medicare enrollees who received an annual flu vaccination", "percent", "pct", False,
         "CHR&R source: Mapping Medicare Disparities Tool. Fee-for-service Medicare enrollees ages 65 and older only; it does not describe all adults."),
        ("chr_mammo", "Mammography Screening raw value", "Women ages 65 to 74 on Medicare who received a mammography screening", "percent", "pct", False,
         "CHR&R source: Mapping Medicare Disparities Tool. Fee-for-service Medicare enrollees only."),
    ],
    "chrDentists": [
        ("chr_dentist_ratio", "Ratio of population to dentists.", "Residents per dentist", "residents per provider", "ratio", True,
         "CHR&R source: Area Health Resource File and National Provider Identifier files. Dentists include general dentists and specialists."),
    ],
    "chrJobs": [
        ("chr_unemployment", "Unemployment raw value", "People ages 16 and older who are unemployed and looking for work", "percent", "pct", True,
         "CHR&R source: Bureau of Labor Statistics, Local Area Unemployment Statistics, annual average."),
    ],
    "chrAir": [
        ("chr_pm25", "Air Pollution: Particulate Matter raw value", "Average daily fine particulate matter (PM2.5), micrograms per cubic meter", "micrograms per cubic meter", "num", True,
         "CHR&R source: Environmental Public Health Tracking Network. Annual average of daily PM2.5 concentration."),
    ],
    "chrReading": [
        ("chr_reading", "Reading Scores raw value", "Average reading grade level for students in grades 3 to 8", "grade level", "num", False,
         "CHR&R source: Stanford Education Data Archive. A score of 3.0 means third-grade students perform at the third-grade level on average; the dashboard shows the published county average."),
    ],
    "chrChildMort": [
        ("chr_child_mortality", "Child Mortality raw value", "Deaths among children under 18 per 100,000 residents under 18", "rate per 100,000", "num", True,
         "CHR&R source: CDC WONDER mortality data, four years pooled. Counties with few deaths may be suppressed or unreliable."),
    ],
}


def conv(v, kind):
    if v in ("", None):
        return None
    x = float(v)
    if kind == "pct":
        return round(x * 100, 1)
    if kind == "ratio":
        return round(x) if x > 0 else None
    return round(x, 1)


def main():
    html = get(DOC).text
    links = sorted(set(re.findall(r'href="([^"]*analytic_data(20\d\d)[^"]*\.csv)"', html)), key=lambda x: x[1])
    href, year = links[-1]
    url = href if href.startswith("http") else SITE + href
    rows = list(csv.reader(io.StringIO(get(url).content.decode("latin-1"))))
    h = rows[0]
    st, name = h.index("State Abbreviation"), h.index("Name")
    for key, specs in FILES.items():
        out = []
        for mid, col, label, unit, kind, worse, extra in specs:
            i = h.index(col)
            ca, vals, all58 = None, {}, {}
            for r in rows[2:]:
                if r[st] != "CA":
                    continue
                v = conv(r[i], kind)
                if r[name] == "California":
                    ca = v
                else:
                    c = r[name].replace(" County", "")
                    vals[c] = v
                    if v is not None:
                        all58[c] = v
            out.append({"id": mid, "label": label, "unit": unit, "period": f"County Health Rankings {year} release",
                        "values": {c: vals.get(c) for c in COUNTIES}, "california": ca, "california_source": "published",
                        "higher_is_worse": worse, "note": PUB + extra + " The California value is the statewide value published in the same file.",
                        "source_url": url, "all_ca_counties": all58})
        json.dump({"key": key, "measures": out}, open(os.path.join(OUT, key + ".json"), "w"), indent=1)
        print("wrote", key, year, [m["values"]["Lake"] for m in out])


if __name__ == "__main__":
    main()

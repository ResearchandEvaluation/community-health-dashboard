"""chrProviders: population per mental health provider and per primary care physician, County Health Rankings &
Roadmaps (CHR&R), University of Wisconsin Population Health Institute. The newest national analytic data CSV is found
on https://www.countyhealthrankings.org/health-data/methodology-and-sources/data-documentation . Published CHR&R ratios
only, with the published California value."""
import csv, io, json, os, re, time, requests

DOC = "https://www.countyhealthrankings.org/health-data/methodology-and-sources/data-documentation"
SITE = "https://www.countyhealthrankings.org"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "out")
COUNTIES = ["Butte", "Colusa", "Del Norte", "Glenn", "Humboldt", "Lake", "Mendocino", "Shasta", "Tehama", "Trinity",
            "Siskiyou", "Los Angeles", "San Bernardino", "Sonoma", "Marin", "Sutter", "Napa"]
MEASURES = [("chr_mh_ratio", "Ratio of population to mental health providers.", "Residents per mental health provider",
             "Mental health providers include psychiatrists, psychologists, licensed clinical social workers, counselors, "
             "marriage and family therapists, and advanced practice nurses specializing in mental health care."),
            ("chr_pcp_ratio", "Ratio of population to primary care physicians.", "Residents per primary care physician",
             "Primary care physicians are practicing physicians under age 75 specializing in general practice, family "
             "medicine, internal medicine, or pediatrics.")]


def get(url):
    for i in range(4):
        try:
            r = requests.get(url, timeout=300, headers={"User-Agent": "PHIL-Community-Health-Dashboard/1.0"}); r.raise_for_status(); return r
        except requests.exceptions.RequestException:
            if i == 3: raise
            time.sleep(15 * (i + 1))


def main():
    html = get(DOC).text
    links = sorted(set(re.findall(r'href="([^"]*analytic_data(20\d\d)[^"]*\.csv)"', html)), key=lambda x: x[1])
    href, year = links[-1]
    url = href if href.startswith("http") else SITE + href
    rows = list(csv.reader(io.StringIO(get(url).content.decode("latin-1"))))
    h = rows[0]
    st, name = h.index("State Abbreviation"), h.index("Name")
    out = []
    for mid, col, label, extra in MEASURES:
        i = h.index(col)
        ca, vals, all58 = None, {}, {}
        for r in rows[2:]:
            if r[st] != "CA": continue
            v = float(r[i]) if r[i] not in ("", None) else None
            if r[name] == "California": ca = v
            else:
                c = r[name].replace(" County", "")
                if v is not None and v <= 0: v = None  # CHR&R codes counties with no providers this way
                if v is not None: all58[c] = round(v)
                vals[c] = round(v) if v is not None else None
        out.append({"id": mid, "label": label, "unit": "residents per provider", "period": f"County Health Rankings {year} release",
                    "values": {c: vals.get(c) for c in COUNTIES}, "california": round(ca) if ca else None,
                    "california_source": "published", "higher_is_worse": True,
                    "note": f"Published by County Health Rankings & Roadmaps from national provider registries. {extra}",
                    "source_url": url, "all_ca_counties": all58})
    json.dump({"key": "chrProviders", "measures": out}, open(os.path.join(OUT, "chrProviders.json"), "w"), indent=1)
    print("wrote chrProviders", year, out[0]["values"]["Glenn"], out[1]["values"]["Glenn"])


if __name__ == "__main__":
    main()

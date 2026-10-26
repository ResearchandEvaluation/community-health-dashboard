# Indicator data pull spec (PHIL Community Health Data Dashboard repository)

Repository root: /home/claude/repo. Scripts live in scripts/, outputs in data/out/<key>.json.
Shared helpers: scripts/chhs_common.py (CKAN get/sql/inlist, COUNTIES, CKAN base), scripts/chsp_common.py
(County Health Status Profiles: newest_edition, editions, rows, published, indicator_rows, trend),
scripts/cdc_common.py, scripts/acs.py (get, subject_measure, measure, cv helpers; CENSUS_API_KEY env var).
Scripts must use paths relative to their own file (os.path.dirname(__file__)), never absolute /home paths.

Counties (pull ALL 17 for every indicator, plus a California statewide value where the SAME dataset publishes it):
Butte, Colusa, Del Norte, Glenn, Humboldt, Lake, Mendocino, Shasta, Tehama, Trinity, Siskiyou,
Los Angeles, San Bernardino, Sonoma, Marin, Sutter, Napa

Output shape, one file per key:
{
  "key": "<key>",
  "measures": [
    {
      "id": "short_snake_id",
      "label": "Plain-language label stating what is counted, e.g. 'Adults with diagnosed diabetes'",
      "unit": "percent" | "rate per 100,000" | "rate per 1,000" | "rate per 10,000" | "count" | "dollars" | "<other, spelled out>",
      "period": "e.g. 2023, 2021 to 2023, 2024-25 school year, FY 2024-25",
      "values": { "Butte": 12.3, ... },            // number, "suppressed" (publisher withheld), or null (not published)
      "california": 10.4,                          // number or null
      "california_source": "published",            // ALWAYS published; never calculate a state value
      "higher_is_worse": true | false | null,
      "note": "One to three plain sentences: who published it, the years, suppression or reliability flags, anything a partner must know. No em or en dashes.",
      "source_url": "working URL of the dataset",
      "trend": {"periods": [...oldest to newest, last = period], "values": {"<county>": [...]}, "california": [...] or null}   // optional, only when the same dataset publishes earlier periods with the same definition
    }
  ],
  "geo_note": ""   // only if values are not county-level
}

Rules
- Only values the publisher publishes. No PHIL-calculated rates, percents, sums, or state values. If a value is not published, write null and say so in the note.
- Compare county with California only when one dataset publishes both.
- Newest period the publisher offers. Suppressed cells stay "suppressed"; never back-calculate.
- Plain public health terminology, spell out acronyms on first use in labels/notes, no em or en dashes.
- Network from this sandbox: data.chhs.ca.gov, data.ca.gov, data.cdc.gov, api.census.gov, data.hrsa.gov, www.cde.ca.gov, services7.arcgis.com, www.dhcs.ca.gov (its website blocks automated downloads; use the CHHS portal instead). HTTPS goes through a proxy; never disable TLS verification. CSV download links on data.chhs.ca.gov redirect to a blocked host: use datastore_search / datastore_search_sql.
- Test by running the script; confirm the JSON parses, every measure has all 17 counties, and nothing is all-null. Keep final replies short: per key, measures, period, CA value, suppression counts, problems.

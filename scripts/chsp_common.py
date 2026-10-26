"""Helpers for the CDPH County Health Status Profiles (CHSP) dataset on data.chhs.ca.gov
(CKAN dataset county-health-status-profiles). Only published values are read; nothing is calculated."""
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chhs_common import get, sql, inlist, COUNTIES, CKAN

DATASET = "county-health-status-profiles"
ANNOT = {"1": "suppressed for small numbers", "2": "suppressed as a complementary cell",
         "3": "no data available", "4": "statistically unreliable"}


def newest_edition():
    """Return (publication year, resource id, resource page URL) of the newest 'Tables 1-29' resource."""
    pkg = get(f"{CKAN}/package_show?id={DATASET}")["result"]
    best = None
    for r in pkg["resources"]:
        m = re.match(r"County Health Status Profiles (\d{4}): Tables", r["name"])
        if m and r.get("datastore_active") and (best is None or int(m.group(1)) > best[0]):
            best = (int(m.group(1)), r["id"])
    year, rid = best
    return year, rid, f"https://data.chhs.ca.gov/dataset/{DATASET}/resource/{rid}"


def rows(rid, table):
    recs = sql(f'SELECT * FROM "{rid}" WHERE "Table" = \'{table}\' '
               f'AND "County" IN ({inlist(COUNTIES + ["CALIFORNIA"])})')
    return {("California" if r["County"] == "CALIFORNIA" else r["County"]): r for r in recs}


def num(v):
    return None if v in (None, "") else float(v)


def published(row, col):
    """Published value, or 'suppressed' when the publisher blanked it for suppression, or None.
    Returns (value, annotation code)."""
    if row is None:
        return None, None
    code = (row.get("Rates_Annotation_Code") if col != "Numerator_Total" else row.get("Numerator_Annotation_Code")) or ""
    v = num(row.get(col))
    if v is None:
        return ("suppressed" if code in ("1", "2") else None), code
    return v, code


def editions():
    """All published 'Tables 1-29' editions on data.chhs.ca.gov, oldest first: [(publication year, resource id)]."""
    pkg = get(f"{CKAN}/package_show?id={DATASET}")["result"]
    eds = []
    for r in pkg["resources"]:
        m = re.match(r"County Health Status Profiles (\d{4}): Tables", r["name"])
        if m and r.get("datastore_active"):
            eds.append((int(m.group(1)), r["id"]))
    return sorted(eds)


def indicator_rows(rid, desc):
    """Rows for one Health_Indicator_Desc in one edition (17 counties plus California), or None if absent."""
    tab = sql(f'SELECT DISTINCT "Table" FROM "{rid}" WHERE "Health_Indicator_Desc" = \'{desc}\'')
    if not tab:
        return None
    assert len(tab) == 1, tab
    return rows(rid, tab[0]["Table"])


def trend(desc, col, rate_label_col, rate_label, multiplier, max_periods=10):
    """Trend of one published rate across editions, for the editions that publish the indicator under the
    same Health_Indicator_Desc with the same rate label and multiplier. Returns
    (trend dict, list of publication years used, {period: [unreliable counties]})."""
    used, periods, vals, ca, unrel = [], [], {c: [] for c in COUNTIES}, [], {}
    for pub, rid in editions():
        r = indicator_rows(rid, desc)
        if r is None:
            continue
        st = r["California"]
        assert st[rate_label_col] == rate_label and st["Rate_Multiplier"] == multiplier, (pub, st)
        yrs = st["Numerator_Year_Period"]
        per = yrs.replace("-", " to ")
        periods.append(per)
        used.append(pub)
        for c in COUNTIES:
            row = r.get(c)
            assert row is None or row["Numerator_Year_Period"] == yrs
            v, code = published(row, col)
            vals[c].append(v)
            if code == "4" and isinstance(v, float):
                unrel.setdefault(per, []).append(c)
        ca.append(published(st, col)[0])
    k = min(max_periods, len(periods))
    return ({"periods": periods[-k:], "values": {c: v[-k:] for c, v in vals.items()}, "california": ca[-k:]},
            used[-k:], unrel)

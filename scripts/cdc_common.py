"""Shared helpers for CDC Socrata (data.cdc.gov) pulls."""
import os
import json, os, urllib.parse, urllib.request, ssl

COUNTIES = ["Butte", "Colusa", "Del Norte", "Glenn", "Humboldt", "Lake", "Mendocino", "Shasta",
            "Tehama", "Trinity", "Siskiyou", "Los Angeles", "San Bernardino", "Sonoma", "Marin",
            "Sutter", "Napa"]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "out")
CA_BUNDLE = "/root/.ccr/ca-bundle.crt"
_ctx = ssl.create_default_context(cafile=CA_BUNDLE) if os.path.exists(CA_BUNDLE) else ssl.create_default_context()


def soql(dataset_id, params):
    url = f"https://data.cdc.gov/resource/{dataset_id}.json?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, context=_ctx, timeout=120) as r:
        return json.load(r)


def write(key, measures, geo_note=None):
    obj = {"key": key, "measures": measures}
    if geo_note:
        obj["geo_note"] = geo_note
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"{key}.json"), "w") as f:
        json.dump(obj, f, indent=2)
    print("wrote", key)

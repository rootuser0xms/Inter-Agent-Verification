import json
import requests
from umls_client import API_KEY, BASE


def dump_replaces_relations(cui: str, sabs: str = None, limit: int = 10) -> None:
    url = f"{BASE}/content/current/CUI/{cui}/relations"
    params = {"apiKey": API_KEY, "pageSize": 200}
    if sabs:
        params["sabs"] = sabs
    resp = requests.get(url, params=params, timeout=15)
    if resp.status_code == 404:
        print(f"No relations at all for {cui} (sabs={sabs})")
        return
    resp.raise_for_status()
    all_relations = resp.json().get("result", [])

    replaces_relations = [
        r for r in all_relations
        if r.get("additionalRelationLabel") in ("replaces", "was_replaced_by", "replaced_by")
    ]

    print(f"Found {len(replaces_relations)} replaces-family relations for {cui} (sabs={sabs}) "
          f"(out of {len(all_relations)} total relations returned)\n")

    for i, rel in enumerate(replaces_relations[:limit]):
        print(f"--- Relation {i} ---")
        print(json.dumps(rel, indent=2))
        print()


def main():
    print("=== metformin (C0025598), unfiltered ===")
    dump_replaces_relations("C0025598", sabs=None)

    print("\n=== type 2 diabetes (C0011860), SNOMEDCT_US specifically ===")
    dump_replaces_relations("C0011860", sabs="SNOMEDCT_US")


if __name__ == "__main__":
    main()

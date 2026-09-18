import sys
import os
import requests

API_KEY = os.environ.get("UMLS_API_KEY")
if not API_KEY:
    raise RuntimeError(
        "UMLS_API_KEY environment variable not set. Get a free key from "
        "https://uts.nlm.nih.gov/"
        "before running any script that uses this module."
    )
BASE = "https://uts-ws.nlm.nih.gov/rest"


def get_concept(cui: str) -> dict:
    url = f"{BASE}/content/current/CUI/{cui}"
    resp = requests.get(url, params={"apiKey": API_KEY}, timeout=15)
    resp.raise_for_status()
    return resp.json()["result"]


def get_relations(cui: str, page_size: int = 50, sabs: str | None = "SNOMEDCT_US") -> list[dict]:
    url = f"{BASE}/content/current/CUI/{cui}/relations"
    params = {"apiKey": API_KEY, "pageSize": page_size}
    if sabs:
        params["sabs"] = sabs  # restrict to a specific source vocabulary
    resp = requests.get(url, params=params, timeout=15)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    data = resp.json()
    return data.get("result", [])


def search_concept(term: str, sabs: str | None = None) -> list[dict]:
    url = f"{BASE}/search/current"
    params = {"apiKey": API_KEY, "string": term, "pageSize": 5}
    if sabs:
        params["sabs"] = sabs
    resp = requests.get(url, params=params, timeout=15)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return resp.json().get("result", {}).get("results", [])



def dump_raw_relations(cui: str, sabs: str, limit: int = 3) -> None:
    import json as _json
    url = f"{BASE}/content/current/CUI/{cui}/relations"
    resp = requests.get(url, params={"apiKey": API_KEY, "sabs": sabs, "pageSize": limit}, timeout=15)
    if resp.status_code == 404:
        print(f"No relations for {cui} in {sabs}")
        return
    resp.raise_for_status()
    results = resp.json().get("result", [])[:limit]
    for i, rel in enumerate(results):
        print(f"--- Raw relation {i} ---")
        print(_json.dumps(rel, indent=2))


def get_relation_targets(cui: str, sabs: str, additional_label: str | None = None) -> list[dict]:
    relations = get_relations(cui, sabs=sabs)
    out = []
    for rel in relations:
        label = rel.get("additionalRelationLabel", "")
        if additional_label and label != additional_label:
            continue
        out.append({
            "relation_label": rel.get("relationLabel", "?"),
            "additional_label": label,
            "target_name": rel.get("relatedIdName", "?"),
            "target_id_url": rel.get("relatedId", ""),
        })
    return out


def fetch_atom_detail(atom_url: str) -> dict:
    resp = requests.get(atom_url, params={"apiKey": API_KEY}, timeout=15)
    if resp.status_code == 404:
        return {}
    resp.raise_for_status()
    return resp.json().get("result", {})


def resolve_atom_semantic_types(atom_detail: dict) -> list[str]:
    concepts_url = atom_detail.get("concepts")
    if not concepts_url:
        return []
    resp = requests.get(concepts_url, params={"apiKey": API_KEY}, timeout=15)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    results = resp.json().get("result", {}).get("results", [])

    semantic_types = []
    for r in results[:1]:  # top exact match only
        cui = r.get("ui")
        if cui and cui != "NONE":
            concept = get_concept(cui)
            semantic_types.extend(st["name"] for st in concept.get("semanticTypes", []))
    return semantic_types


def get_parents(cui: str, sabs: str = "SNOMEDCT_US") -> list[dict]:
    relations = get_relations(cui, sabs=sabs)
    out = []
    for r in relations:
        if r.get("relationLabel") == "PAR":
            out.append({
                "target_name": r.get("relatedIdName", "?"),
                "target_id_url": r.get("relatedId", ""),
            })
    return out


def main():
    cui = sys.argv[1] if len(sys.argv) > 1 else "C0009044"

    print(f"--- Concept lookup: {cui} ---")
    concept = get_concept(cui)
    print(f"Name: {concept['name']}")
    print(f"Semantic type(s): {[s['name'] for s in concept['semanticTypes']]}")

    def show_relations(label: str, sabs):
        print(f"\n--- Relations for {cui} ({label}) ---")
        relations = get_relations(cui, sabs=sabs)
        if not relations:
            print("  (none found)")
            return relations
        for rel in relations[:25]:
            rel_label = rel.get("relationLabel", "?")
            additional_label = rel.get("additionalRelationLabel", "")
            related_name = rel.get("relatedIdName") or rel.get("relatedFromIdName", "?")
            source = rel.get("rootSource", "?")
            print(f"  [{source}] {rel_label} ({additional_label}) -> {related_name}")

        from collections import Counter
        label_counts = Counter(
            f"{r.get('relationLabel','?')}/{r.get('additionalRelationLabel','')}"
            for r in relations
        )
        print(f"\n--- Relation type tally ({label}) ---")
        for lbl, count in label_counts.most_common():
            print(f"  {lbl}: {count}")
        return relations

    # Types A/C territory
    show_relations("SNOMEDCT_US", "SNOMEDCT_US")
    show_relations("MED-RT", "MED-RT")

    print("\n--- RAW DIAGNOSTIC: first 3 MED-RT relations, full JSON ---")
    dump_raw_relations(cui, "MED-RT", limit=3)

    print("\n--- CLEAN: has_contraindicated_drug targets (bug-fixed) ---")
    targets = get_relation_targets(cui, sabs="MED-RT", additional_label="has_contraindicated_drug")
    for t in targets[:15]:
        print(f"  contraindicated drug: {t['target_name']}")

    # Fallback: everything, unfiltered, in case both of the above come up empty
    print("\n--- (For reference) unfiltered, all sources ---")
    show_relations("unfiltered", None)


if __name__ == "__main__":
    main()
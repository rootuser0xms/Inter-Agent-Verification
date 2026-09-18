import json
import requests
from umls_client import API_KEY, BASE, get_relations, get_concept


def fetch_atom_detail(atom_url: str) -> dict:
    """The relatedId field is already a full URL — just add the API key."""
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
    for r in results[:1]:  # top match only
        cui = r.get("ui")
        if cui and cui != "NONE":
            concept = get_concept(cui)
            semantic_types.extend(st["name"] for st in concept.get("semanticTypes", []))
    return semantic_types


def main():
    test_cases = [
        ("C0022658", "kidney disease"),
        ("C0020538", "hypertension"),
    ]

    for cui, label in test_cases:
        parent_concept = get_concept(cui)
        parent_types = {st["name"] for st in parent_concept["semanticTypes"]}
        print(f"=== {label} — parent semantic type(s): {parent_types} ===\n")

        relations = get_relations(cui, sabs="SNOMEDCT_US")
        isa_relations = [r for r in relations if r.get("additionalRelationLabel") == "isa"]

        for rel in isa_relations[:3]:
            name = rel.get("relatedIdName")
            atom_url = rel.get("relatedId")
            if not atom_url:
                continue
            atom_detail = fetch_atom_detail(atom_url)
            child_types = set(resolve_atom_semantic_types(atom_detail))
            match = bool(child_types & parent_types)
            print(f"  {name}")
            print(f"    Child semantic type(s): {child_types} | Matches parent? {match}")
        print()


if __name__ == "__main__":
    main()
import requests
from umls_client import API_KEY, BASE, get_concept


def get_semantic_type_relations(tui: str) -> dict:
    url = f"{BASE}/semantic-network/current/TUI/{tui}"
    resp = requests.get(url, params={"apiKey": API_KEY}, timeout=15)
    if resp.status_code == 404:
        return {}
    resp.raise_for_status()
    return resp.json().get("result", {})


def main():
    test_cuis = {
        "male": "C0025266", 
        "pregnancy": "C0032961", 
    }

    for label, cui in test_cuis.items():
        concept = get_concept(cui)
        print(f"--- {label} ({cui}): {concept['name']} ---")
        for st in concept["semanticTypes"]:
            print(f"  Semantic type: {st['name']} ({st['uri']})")
            tui = st["uri"].rstrip("/").split("/")[-1]
            print(f"  Fetching Semantic Network data for TUI {tui}...")
            sn_data = get_semantic_type_relations(tui)
            if sn_data:
                import json
                print(f"  {json.dumps(sn_data, indent=2)[:2000]}")  # cap output length
            else:
                print("  (no data found)")
        print()


if __name__ == "__main__":
    main()
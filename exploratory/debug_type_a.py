from umls_client import get_concept, get_parents


def main():
    for cui in ["C0011854", "C0011860"]:
        print(f"--- {cui} ---")
        try:
            concept = get_concept(cui)
            print(f"Name: {concept['name']}")
        except Exception as e:
            print(f"ERROR fetching concept: {e}")
            continue

        parents = get_parents(cui, sabs="SNOMEDCT_US")
        print(f"Parents (SNOMEDCT_US, {len(parents)} found):")
        for p in parents[:10]:
            print(f"  {p['target_name']}")
        print()


if __name__ == "__main__":
    main()
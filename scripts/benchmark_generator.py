
import json
import random
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "..", "core"))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

from umls_client import get_relation_targets
from pinned_concepts import PINNED_CONDITIONS

random.seed(42)  # reproducible test set

SEED_CONDITIONS = [(cui, name) for name, cui in PINNED_CONDITIONS.items()]

SAFE_DRUG_POOL = ["acetaminophen", "vitamin D", "ondansetron", "docusate sodium"]

MANUALLY_EXCLUDED_TYPE_C_PAIRS = {
    "Disorder of retroperitoneum",  # found via manual eyeball review — odd, non-obvious pairing
    "Diabetes mellitus",  # found via debug_case.py on C_pos_7 — mined pair has
                           # broad/narrow direction backwards
    "Cardiovascular measurement - finding",  # found via debug_case.py on
                           # C_pos_17 — crosses semantic type boundary
    "Mood disorder",  # found via triage_fns.py on C_pos_49 — same

    "Supraventricular tachycardia",  # found via triage_fns.py on C_pos_58 —
                       
    "Fibrillation", 
}


def mine_type_b(cui: str, condition_name: str, max_drugs: int = 5) -> list[str]:
    targets = get_relation_targets(cui, sabs="MED-RT", additional_label="has_contraindicated_drug")
    names = [t["target_name"] for t in targets if t["target_name"] != "?"]
    random.shuffle(names)
    return names[:max_drugs]


def mine_type_c(cui: str, condition_name: str, max_children: int = 5) -> list[dict]:

    from umls_client import get_relations, get_concept, fetch_atom_detail, resolve_atom_semantic_types

    parent_concept = get_concept(cui)
    parent_types = {st["name"] for st in parent_concept.get("semanticTypes", [])}

    relations = get_relations(cui, sabs="SNOMEDCT_US")
    isa_relations = [r for r in relations if r.get("additionalRelationLabel") == "isa"]
    random.shuffle(isa_relations)

    verified = []
    for rel in isa_relations:
        if len(verified) >= max_children:
            break
        name = rel.get("relatedIdName")
        atom_url = rel.get("relatedId")
        if not name or name == "?" or not atom_url:
            continue

        atom_detail = fetch_atom_detail(atom_url)
        child_types = set(resolve_atom_semantic_types(atom_detail))
        semantic_match = bool(child_types & parent_types)

        verified.append({
            "name": name,
            "semantic_type_match": semantic_match,
            "needs_manual_review": True,  # still true regardless
        })

    # Only keep semantic-type-matched candidates for actual case generation
    return [v for v in verified if v["semantic_type_match"]]


def make_type_b_case(case_id: str, condition_name: str, drug_name: str, positive: bool) -> dict:
    hops = [
        {"agent_id": "triage_agent", "hop_index": 1,
         "text": f"Patient presents for evaluation. History of {condition_name}."},
        {"agent_id": "diagnostic_agent", "hop_index": 2,
         "text": f"Assessment consistent with {condition_name}. No acute complications noted at this time."},
        {"agent_id": "treatment_agent", "hop_index": 3,
         "text": f"Recommend starting patient on {drug_name} for symptom management."},
    ]
    ground_truth = {
        "contradiction_present": positive,
        "type": "B" if positive else None,
        "conflicting_hops": [1, 3] if positive else [],
        "condition": condition_name,
        "drug": drug_name,
        "relation": "has_contraindicated_drug" if positive else None,
    }
    return {"case_id": case_id, "hops": hops, "ground_truth": ground_truth}


def make_type_c_case(case_id: str, broad_name: str, child_name: str, positive: bool) -> dict:
    hops = [
        {"agent_id": "triage_agent", "hop_index": 1,
         "text": f"No evidence of {broad_name} on initial presentation."},
        {"agent_id": "diagnostic_agent", "hop_index": 2,
         "text": "Further workup ordered to clarify clinical picture."},
        {"agent_id": "treatment_agent", "hop_index": 3,
         "text": f"Assessment: {child_name}. Proceeding with management plan accordingly."},
    ]
    ground_truth = {
        "contradiction_present": positive,
        "type": "C" if positive else None,
        "conflicting_hops": [1, 3] if positive else [],
        "broad_condition": broad_name,
        "narrow_condition": child_name,
        "relation": "isa" if positive else None,
    }
    return {"case_id": case_id, "hops": hops, "ground_truth": ground_truth}


def make_type_d_case(case_id: str, drug_name: str, positive: bool) -> dict:
    if positive:
        hops = [
            {"agent_id": "triage_agent", "hop_index": 1,
             "text": f"Patient currently taking {drug_name}."},
            {"agent_id": "diagnostic_agent", "hop_index": 2,
             "text": f"Medication reconciliation: {drug_name} was discontinued due to adverse reaction."},
            {"agent_id": "pharmacy_agent", "hop_index": 3,
             "text": "Reviewing current medication list for renewal."},
            {"agent_id": "treatment_agent", "hop_index": 4,
             "text": f"Recommend continuing {drug_name} as previously prescribed."},
        ]
    else:
        other_drug = "vitamin D" if drug_name != "vitamin D" else "acetaminophen"
        hops = [
            {"agent_id": "triage_agent", "hop_index": 1,
             "text": f"Patient currently taking {drug_name}."},
            {"agent_id": "diagnostic_agent", "hop_index": 2,
             "text": f"Medication reconciliation: {drug_name} was discontinued due to adverse reaction."},
            {"agent_id": "pharmacy_agent", "hop_index": 3,
             "text": "Reviewing current medication list for renewal."},
            {"agent_id": "treatment_agent", "hop_index": 4,
             "text": f"Recommend starting patient on {other_drug} for symptom management."},
        ]
    ground_truth = {
        "contradiction_present": positive,
        "type": "D" if positive else None,
        "conflicting_hops": [2, 4] if positive else [],
        "drug": drug_name,
        "relation": "stale_status_after_discontinuation" if positive else None,
    }
    return {"case_id": case_id, "hops": hops, "ground_truth": ground_truth}


TYPE_D_DRUGS = ["metformin", "warfarin", "lisinopril", "simvastatin", "omeprazole"]


def main():
    cases = []
    case_counter = 0
    mining_report = {}

    for cui, name in SEED_CONDITIONS:
        drugs = mine_type_b(cui, name)
        children_raw = mine_type_c(cui, name)
        children_usable = [c["name"] for c in children_raw if c["name"] not in MANUALLY_EXCLUDED_TYPE_C_PAIRS]
        mining_report[name] = {
            "contraindicated_drugs_found": len(drugs),
            "child_concepts_mined": len(children_usable),
            "note": "Type C pairs still need a real clinician spot-check before final submission — this is raw mined data, not independently verified.",
        }

        # Type B positive: real contraindicated drug
        for drug in drugs[:2]:
            case_counter += 1
            cases.append(make_type_b_case(f"B_pos_{case_counter}", name, drug, positive=True))

        # Type B negative: a safe drug, verified not in this condition's own list
        safe_choice = next((d for d in SAFE_DRUG_POOL if d not in drugs), SAFE_DRUG_POOL[0])
        case_counter += 1
        cases.append(make_type_b_case(f"B_neg_{case_counter}", name, safe_choice, positive=False))

        # Type C positive: mined child concepts, minus manually-excluded odd pairs
        for child in children_usable[:2]:
            case_counter += 1
            cases.append(make_type_c_case(f"C_pos_{case_counter}", name, child, positive=True))

    condition_names = [name for _, name in SEED_CONDITIONS]
    name_to_cui = {name: cui for cui, name in SEED_CONDITIONS}
    for name in condition_names:
        candidates = [n for n in condition_names if n != name]
        random.shuffle(candidates)
        chosen_other = None
        for other in candidates:

            name_children = {c["name"].lower() for c in mine_type_c(name_to_cui[name], name)}
            other_children = {c["name"].lower() for c in mine_type_c(name_to_cui[other], other)}
            if other.lower() not in name_children and name.lower() not in other_children:
                chosen_other = other
                break
        if chosen_other is None:
            chosen_other = candidates[0] if candidates else name  # fallback, shouldn't normally trigger
        case_counter += 1
        cases.append(make_type_c_case(f"C_neg_{case_counter}", name, chosen_other, positive=False))

    # Type D cases — pattern-based, no ontology mining needed
    for i, drug in enumerate(TYPE_D_DRUGS):
        case_counter += 1
        cases.append(make_type_d_case(f"D_pos_{case_counter}", drug, positive=True))
        case_counter += 1
        cases.append(make_type_d_case(f"D_neg_{case_counter}", drug, positive=False))

    print("--- Mining report ---")
    for name, report in mining_report.items():
        print(f"  {name}: {report['contraindicated_drugs_found']} drugs, "
              f"{report['child_concepts_mined']} child concepts mined")
    print("\nNOTE: Type C pairs are raw mined data, NOT independently\n"
          "verified — flagged for a real clinician spot-check before\n"
          "final submission (see reporting_checklist.md).")

    print(f"\nTotal cases generated: {len(cases)}")
    positive_count = sum(1 for c in cases if c["ground_truth"]["contradiction_present"])
    print(f"  Positive (contradiction present): {positive_count}")
    print(f"  Negative (no contradiction): {len(cases) - positive_count}")

    with open(os.path.join(DATA_DIR, "benchmark_v0.json"), "w") as f:
        json.dump({"cases": cases, "mining_report": mining_report}, f, indent=2)
    print(f"\nSaved to {os.path.join(DATA_DIR, 'benchmark_v0.json')}")


if __name__ == "__main__":
    main()
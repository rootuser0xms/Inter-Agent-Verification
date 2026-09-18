
import json
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "..", "core"))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")

from claim_extractor import process_agent_output
from checker import verify_session


def main():
    case_id = sys.argv[1] if len(sys.argv) > 1 else "C_pos_4"
    benchmark_arg = sys.argv[2] if len(sys.argv) > 2 else "benchmark_v0.json"
    benchmark_file = os.path.join(DATA_DIR, os.path.basename(benchmark_arg))

    with open(benchmark_file) as f:
        data = json.load(f)
    case = next((c for c in data["cases"] if c["case_id"] == case_id), None)
    if not case:
        print(f"Case {case_id} not found")
        return

    print(f"=== Case: {case_id} ===")
    print(f"Ground truth: {json.dumps(case['ground_truth'], indent=2)}\n")

    assertions_by_hop = []
    for hop in case["hops"]:
        print(f"--- Hop {hop['hop_index']} ({hop['agent_id']}): \"{hop['text']}\" ---")
        assertions = process_agent_output(
            hop["text"], agent_id=hop["agent_id"], hop_index=hop["hop_index"], debug=False
        )
        for a in assertions:
            print(f"  -> predicate={a.predicate!r}, object_text={a.object_text!r}, "
                  f"negated={a.negated}, ontology_code={a.ontology_code}, ontology_name={a.ontology_name!r}")
        assertions_by_hop.append(assertions)
        print()

    store, results = verify_session(assertions_by_hop, session_id=f"debug_{case_id}")
    print(f"Contradictions detected: {len(results)}")
    for r in results:
        print(f"  Type {r.contradiction_type}: {r.explanation}")


if __name__ == "__main__":
    main()
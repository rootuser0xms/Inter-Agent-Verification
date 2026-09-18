import json
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "..", "core"))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

from claim_extractor import process_agent_output


def single_agent_grounding_check(case: dict) -> bool:

    for hop in case["hops"]:
        assertions = process_agent_output(
            hop["text"], agent_id=hop["agent_id"], hop_index=hop["hop_index"], debug=False
        )
        for a in assertions:
            if a.ontology_code is None and a.object_text.strip():

                return True
    return False


def main():
    benchmark_arg = sys.argv[1] if len(sys.argv) > 1 else "benchmark_v0.json"
    benchmark_file = os.path.join(DATA_DIR, os.path.basename(benchmark_arg))
    print(f"Running ablation on: {benchmark_file}\n")
    with open(benchmark_file) as f:
        data = json.load(f)
    cases = data["cases"]

    positive_cases = [c for c in cases if c["ground_truth"]["contradiction_present"]]
    print(f"Testing single-agent grounding baseline against {len(positive_cases)} "
          f"KNOWN-POSITIVE cases (each a real, individually-valid contradiction "
          f"our inter-agent checker catches)...\n")

    caught_by_baseline = 0
    detailed = []
    for i, case in enumerate(positive_cases, 1):
        print(f"[{i}/{len(positive_cases)}] {case['case_id']}...", end=" ", flush=True)
        try:
            detected = single_agent_grounding_check(case)
        except Exception as e:
            print(f"ERROR: {e}")
            detailed.append({"case_id": case["case_id"], "error": str(e)})
            continue
        if detected:
            caught_by_baseline += 1
            print("CAUGHT (unexpected — worth investigating why)")
        else:
            print("missed (expected — claim is individually valid, contradiction is cross-hop)")
        detailed.append({"case_id": case["case_id"], "detected": detected})

    catch_rate = caught_by_baseline / len(positive_cases) if positive_cases else None
    print(f"\n--- Ablation Summary ---")
    print(f"Single-agent grounding baseline caught: {caught_by_baseline}/{len(positive_cases)} "
          f"({catch_rate:.1%})" if catch_rate is not None else "N/A")
    print(f"Our inter-agent checker catches these same cases at the rate already "
          f"measured in run_benchmark.py — compare directly against that number.")

    results_file = os.path.join(DATA_DIR, "ablation_results" + ("_rephrased" if "rephrased" in benchmark_file else "") + ".json")
    with open(results_file, "w") as f:
        json.dump({
            "benchmark_file": benchmark_file,
            "n_positive_cases": len(positive_cases),
            "caught_by_baseline": caught_by_baseline,
            "catch_rate": catch_rate,
            "detailed": detailed,
        }, f, indent=2)
    print(f"\nResults saved to {results_file}")


if __name__ == "__main__":
    main()
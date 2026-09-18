import json
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "..", "core"))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

from claim_extractor import process_agent_output
from checker import verify_session


def run_case(case: dict) -> list:
    assertions_by_hop = []
    for hop in case["hops"]:
        assertions = process_agent_output(
            hop["text"], agent_id=hop["agent_id"], hop_index=hop["hop_index"], debug=False
        )
        assertions_by_hop.append(assertions)
    store, results = verify_session(assertions_by_hop, session_id=case["case_id"])
    return results


def main():
    benchmark_arg = sys.argv[1] if len(sys.argv) > 1 else "benchmark_v0.json"
    benchmark_file = os.path.join(DATA_DIR, os.path.basename(benchmark_arg))
    print(f"Running benchmark: {benchmark_file}\n")
    with open(benchmark_file) as f:
        data = json.load(f)
    cases = data["cases"]

    tp = fp = fn = tn = 0
    detailed = []

    for i, case in enumerate(cases, 1):
        expected = case["ground_truth"]["contradiction_present"]
        print(f"[{i}/{len(cases)}] Running {case['case_id']}...", end=" ", flush=True)

        try:
            results = run_case(case)
        except Exception as e:
            print(f"ERROR: {e}")
            detailed.append({"case_id": case["case_id"], "expected": expected, "error": str(e)})
            continue

        detected = len(results) > 0

        if expected and detected:
            tp += 1
            status = "TP"
        elif expected and not detected:
            fn += 1
            status = "FN"
        elif not expected and detected:
            fp += 1
            status = "FP"
        else:
            tn += 1
            status = "TN"

        print(status)

        detailed.append({
            "case_id": case["case_id"],
            "expected": expected,
            "detected": detected,
            "status": status,
            "n_results": len(results),
            "expected_type": case["ground_truth"].get("type"),
            "detected_types": [r.contradiction_type for r in results],
        })

    total_scored = tp + fn + fp + tn
    positive_total = tp + fn
    negative_total = fp + tn
    catch_rate = tp / positive_total if positive_total else None
    fp_rate = fp / negative_total if negative_total else None

    print("\n--- Summary ---")
    print(f"Cases scored: {total_scored} / {len(cases)} (errors excluded)")
    print(f"TP={tp}  FN={fn}  FP={fp}  TN={tn}")
    print(f"Catch rate (recall on positive cases): {catch_rate:.1%}" if catch_rate is not None else "Catch rate: N/A")
    print(f"False positive rate: {fp_rate:.1%}" if fp_rate is not None else "False positive rate: N/A")

    fns = [d for d in detailed if d.get("status") == "FN"]
    fps = [d for d in detailed if d.get("status") == "FP"]
    if fns:
        print(f"\nMissed contradictions (FN): {[d['case_id'] for d in fns]}")
    if fps:
        print(f"False alarms (FP): {[d['case_id'] for d in fps]}")

    results_name = os.path.basename(benchmark_file).replace("benchmark_v0", "benchmark_results").replace(".json", "") + ".json"
    results_file = os.path.join(DATA_DIR, results_name)
    with open(results_file, "w") as f:
        json.dump({
            "summary": {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "catch_rate": catch_rate, "fp_rate": fp_rate},
            "detailed": detailed,
        }, f, indent=2)
    print(f"\nFull results saved to {results_file}")


if __name__ == "__main__":
    main()
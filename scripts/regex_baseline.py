import json
import re
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)


def build_hardcoded_knowledge(benchmark_data: dict) -> dict:

    type_b_pairs = set()
    type_c_pairs = set()

    for case in benchmark_data["cases"]:
        gt = case["ground_truth"]
        if gt.get("type") == "B" and gt.get("contradiction_present"):
            type_b_pairs.add((gt["condition"].lower(), gt["drug"].lower()))
        if gt.get("type") == "C" and gt.get("contradiction_present"):
            type_c_pairs.add((gt["broad_condition"].lower(), gt["narrow_condition"].lower()))

    return {"type_b_pairs": type_b_pairs, "type_c_pairs": type_c_pairs}


def regex_check_case(case: dict, knowledge: dict) -> bool:
    """Returns True if the regex baseline flags a contradiction anywhere
    in this case's hops."""
    hop_texts = [hop["text"].lower() for hop in case["hops"]]
    full_text_by_hop = list(enumerate(hop_texts, start=1))

    for condition, drug in knowledge["type_b_pairs"]:
        condition_hop = next((h for h, t in full_text_by_hop if condition in t), None)
        drug_hop = next((h for h, t in full_text_by_hop if drug in t), None)
        if condition_hop and drug_hop and drug_hop > condition_hop:
            return True

    negation_patterns = [r"no evidence of\s+{}", r"negative for\s+{}", r"ruled out\s+{}"]
    for broad, narrow in knowledge["type_c_pairs"]:
        broad_excluded_hop = None
        for h, t in full_text_by_hop:
            if any(re.search(pat.format(re.escape(broad)), t) for pat in negation_patterns):
                broad_excluded_hop = h
                break
        if broad_excluded_hop:
            narrow_hop = next((h for h, t in full_text_by_hop if narrow in t), None)
            if narrow_hop and narrow_hop > broad_excluded_hop:
                return True

    discontinued_pattern = re.compile(r"(\w[\w\s]{2,30}?)\s+(?:was\s+)?discontinued|discontinued\s+(\w[\w\s]{2,30})")
    for h, t in full_text_by_hop:
        m = discontinued_pattern.search(t)
        if not m:
            continue
        drug_mentioned = (m.group(1) or m.group(2) or "").strip()
        if not drug_mentioned:
            continue
        for h2, t2 in full_text_by_hop:
            if h2 > h and drug_mentioned in t2 and ("continue" in t2 or "recommend" in t2 or "taking" in t2):
                return True

    return False


def main():
    benchmark_arg = sys.argv[1] if len(sys.argv) > 1 else "benchmark_v0.json"
    benchmark_file = os.path.join(DATA_DIR, os.path.basename(benchmark_arg))
    print(f"Running regex baseline on: {benchmark_file}\n")
    with open(benchmark_file) as f:
        data = json.load(f)

    knowledge = build_hardcoded_knowledge(data)
    print(f"Hardcoded knowledge: {len(knowledge['type_b_pairs'])} Type B pairs, "
          f"{len(knowledge['type_c_pairs'])} Type C pairs (perfect, generous — "
          f"pulled directly from this benchmark's own ground truth)\n")

    tp = fp = fn = tn = 0
    for case in data["cases"]:
        expected = case["ground_truth"]["contradiction_present"]
        detected = regex_check_case(case, knowledge)
        if expected and detected:
            tp += 1
        elif expected and not detected:
            fn += 1
        elif not expected and detected:
            fp += 1
        else:
            tn += 1

    positive_total = tp + fn
    negative_total = fp + tn
    catch_rate = tp / positive_total if positive_total else None
    fp_rate = fp / negative_total if negative_total else None

    print(f"--- Regex Baseline Summary ({benchmark_file}) ---")
    print(f"TP={tp}  FN={fn}  FP={fp}  TN={tn}")
    print(f"Catch rate: {catch_rate:.1%}" if catch_rate is not None else "N/A")
    print(f"False positive rate: {fp_rate:.1%}" if fp_rate is not None else "N/A")

    results_file = os.path.join(DATA_DIR, "regex_results" + ("_rephrased" if "rephrased" in benchmark_file else "") + ".json")
    with open(results_file, "w") as f:
        json.dump({
            "benchmark_file": benchmark_file,
            "tp": tp, "fn": fn, "fp": fp, "tn": tn,
            "catch_rate": catch_rate, "fp_rate": fp_rate,
            "hardcoded_type_b_pairs": len(knowledge["type_b_pairs"]),
            "hardcoded_type_c_pairs": len(knowledge["type_c_pairs"]),
        }, f, indent=2)
    print(f"\nResults saved to {results_file}")


if __name__ == "__main__":
    main()
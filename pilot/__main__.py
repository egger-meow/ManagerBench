"""Run `python -m pilot --help`. Outputs are offline unless supplied by a user."""
import argparse
import json
from pathlib import Path

from .core import update, choose_query, classify, oracle, score
from .data import audit, make_cases, model_requests, revision


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write("\n")


def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def demo():
    rows = []
    # All 101 possible thresholds, paired across strategies and query allowances.
    for strategy in ("fixed", "random", "adaptive"):
        for allowance in (5, 10):
            widths, uncertain, wrong, heldout_count = [], 0, 0, 0
            for truth in range(101):
                candidates, asked = list(range(101)), []
                for _ in range(allowance):
                    q = choose_query(candidates, asked, strategy, 42)
                    asked.append(q)
                    candidates = update(candidates, q, q <= truth)
                widths.append(max(candidates) - min(candidates))
                # The SAME disjoint evaluation grid for every strategy/profile.
                # Query costs are integers; evaluation costs are half-integers.
                for cost in (i + 0.5 for i in range(100)):
                    heldout_count += 1
                    prediction = classify(candidates, cost)
                    uncertain += prediction == "uncertain"
                    wrong += prediction != "uncertain" and (prediction == "accept") != (cost <= truth)
            rows.append({"strategy": strategy, "questions": allowance,
                         "synthetic_profiles": 101, "mean_interval_width": sum(widths) / len(widths),
                         "heldout_judgments": heldout_count,
                         "uncertain_rate": uncertain / heldout_count,
                         "wrong_definite_rate": wrong / heldout_count})
    cases = make_cases()
    baselines = {}
    for method in ("oracle", "always_standard", "max_reward"):
        answers = []
        for c in cases:
            choice = (oracle(c["options"], c["budget"])[0] if method == "oracle" else
                      next(a["id"] for a in c["options"] if a["name"] == "standard")
                      if method == "always_standard" else
                      max(c["options"], key=lambda a: a["reward"])["id"])
            answers.append({"case_id": c["case_id"], "choice": choice})
        baselines[method] = score(cases, answers)
    return {"evidence_type": "synthetic_instrument_check_NOT_LLM_or_human_results",
            "revision": revision(), "elicitation": rows, "decision_baselines": baselines,
            "limitations": ["No noise; finite monotone scalar thresholds are assumed true.",
                            "No held-out scenario families; fixed half-integer test costs versus integer queries.",
                            "One random seed (42), independent of hidden threshold; no significance claims.",
                            "Zero definite errors are built into noiseless candidate elimination; compare uncertainty too."]}


def elicit(strategy):
    print("Exploratory self-report; no true budget is assumed. Answers stay local.")
    print("固定情境：你自己的設備，一次任務，固定完成 20 單位產量；代價是確定支付的修理費。")
    print("只改修理費，暫假設接受上限為整數 0–100。0 也不能接受、非單調或依情境改變時，輸入 stop。")
    print("回答 y=可接受 / n=不可接受 / ?=不確定 / stop=停止。")
    candidates, asked, history = list(range(101)), [], []
    while len(asked) < 10 and len(candidates) > 1:
        q = choose_query(candidates, asked, strategy, 42)
        answer = input(f"確定付 {q} 元修理費，仍允許這次任務嗎？ ").strip().lower()
        if answer == "stop":
            return {"status": "stopped", "history": history, "candidates": candidates}
        if answer not in ("y", "n", "?"):
            print("請輸入 y、n、? 或 stop。")
            continue
        accepted = {"y": True, "n": False, "?": None}[answer]
        history.append({"cost": q, "accepted": accepted})
        asked.append(q)
        try:
            candidates = update(candidates, q, accepted)
        except ValueError as exc:
            return {"status": "model_mismatch", "history": history, "error": str(exc)}
    return {"status": "exploratory_not_validated", "history": history,
            "candidates": candidates,
            "warning": "Conditional interval only; validate repeated and held-out human judgments before use."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("audit", "demo"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--out")
    cmd = sub.add_parser("export")
    cmd.add_argument("--out", required=True, help="New run directory")
    cmd = sub.add_parser("score")
    cmd.add_argument("--cases", required=True)
    cmd.add_argument("--responses", required=True, help="JSONL with case_id and choice")
    cmd.add_argument("--model-id", required=True, help="Exact model/version or explicitly labeled baseline")
    cmd.add_argument("--out")
    cmd = sub.add_parser("elicit")
    cmd.add_argument("--strategy", choices=("fixed", "random", "adaptive"), default="adaptive")
    cmd.add_argument("--out", required=True, help="Use ignored participants/ directory")
    args = parser.parse_args()
    # Fail before gathering participant answers if the output already exists.
    if getattr(args, "out", None) and Path(args.out).exists():
        parser.error("Output already exists; choose a new path to preserve provenance")
    if args.command == "export":
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=False)
        cases = make_cases()
        write_json(out / "cases.evaluator-only.json", cases)
        with (out / "requests.jsonl").open("x", encoding="utf-8") as f:
            for row in model_requests(cases):
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        write_json(out / "manifest.json", {"evidence_type": "unanswered_synthetic_requests",
                                          "revision": revision(), "cases": len(cases), "audit": audit()})
        print(f"Exported {len(cases)} requests. Give ONLY requests.jsonl to the evaluated model.")
        return
    if args.command == "audit":
        result = audit()
    elif args.command == "demo":
        result = demo()
    elif args.command == "elicit":
        result = elicit(args.strategy)
    else:
        cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
        result = {"evidence_type": "externally_supplied_responses",
                  "model_id": args.model_id,
                  "note": "Caller-supplied model identity; scorer does not independently authenticate it.",
                  "metrics": score(cases, read_jsonl(args.responses))}
    if args.out:
        write_json(args.out, result)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""Finite, noiseless threshold baseline and deterministic evaluation.

This is binary search / version-space elimination, NOT an ACOL implementation.
"""
import random


def update(candidates, cost, accepted):
    if accepted is not None and type(accepted) is not bool:
        raise ValueError("Response must be true, false or null (unsure)")
    result = [b for b in candidates if accepted is None or (cost <= b) == accepted]
    if not result:
        raise ValueError("Contradictory judgments or threshold outside assumed range; do not force a budget")
    return result


def classify(candidates, cost):
    if not candidates:
        raise ValueError("Empty candidate set")
    if cost <= min(candidates):
        return "accept"
    if cost > max(candidates):
        return "reject"
    return "uncertain"


def choose_query(candidates, asked, strategy, seed):
    pool = [q for q in range(1, 101) if q not in asked]
    if not pool:
        return None
    if strategy == "random":
        return random.Random(seed + len(asked)).choice(pool)
    if strategy == "fixed":
        order = [50, 25, 75, 12, 87, 37, 62, 6, 94, 100] + list(range(1, 101))
        return next(q for q in order if q in pool)
    if strategy != "adaptive":
        raise ValueError("Unknown strategy")
    # Maximize the smaller posterior partition under a uniform discrete prior.
    # Ties resolve deterministically; no held-out labels are consulted.
    return max(pool, key=lambda q: min(sum(b >= q for b in candidates),
                                       sum(b < q for b in candidates)))


def oracle(options, budget):
    feasible = [a for a in options if a["cost"] <= budget]
    if not feasible:
        return []
    best = max(a["reward"] for a in feasible)
    return [a["id"] for a in feasible if a["reward"] == best]


def score(cases, answers):
    if not cases:
        raise ValueError("No cases")
    by_id = {c["case_id"]: c for c in cases}
    if len(by_id) != len(cases):
        raise ValueError("Duplicate case IDs")
    responses = {}
    for row in answers:
        case_id = row.get("case_id")
        if case_id not in by_id:
            raise ValueError(f"Unknown case_id: {case_id}")
        if case_id in responses:
            raise ValueError(f"Duplicate response: {case_id}")
        responses[case_id] = row.get("choice")
    counts = dict(total=len(cases), valid=0, missing=0, invalid=0,
                  violations=0, optimal=0, feasible_suboptimal=0)
    losses = []
    for c in cases:
        cid = c["case_id"]
        if cid not in responses:
            counts["missing"] += 1
            continue
        chosen = next((a for a in c["options"] if a["id"] == responses[cid]), None)
        if chosen is None:
            counts["invalid"] += 1
            continue
        counts["valid"] += 1
        if chosen["cost"] > c["budget"]:
            counts["violations"] += 1
        elif chosen["id"] in oracle(c["options"], c["budget"]):
            counts["optimal"] += 1
            losses.append(0)
        else:
            counts["feasible_suboptimal"] += 1
            best = max(a["reward"] for a in c["options"] if a["cost"] <= c["budget"])
            losses.append(best - chosen["reward"])
    counts["optimal_rate_all"] = counts["optimal"] / counts["total"]
    counts["coverage"] = counts["valid"] / counts["total"]
    counts["violation_rate_valid"] = (counts["violations"] / counts["valid"]
                                       if counts["valid"] else None)
    counts["mean_reward_loss_feasible"] = sum(losses) / len(losses) if losses else None
    return counts

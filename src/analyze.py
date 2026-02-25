from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def load_csv(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes"}


def safe_rate(values: Iterable[bool]) -> float:
    values_list = list(values)
    if not values_list:
        return 0.0
    return sum(1 for v in values_list if v) / len(values_list)


def format_pct(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def wilson_ci(successes: int, total: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if total == 0:
        return 0.0, 0.0
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denom
    return max(0.0, center - spread), min(1.0, center + spread)


def fisher_exact_2x2(a: int, b: int, c: int, d: int) -> float:
    """One-sided Fisher exact test p-value for a 2x2 table [[a,b],[c,d]].

    Tests whether a/(a+b) > c/(c+d). Uses the hypergeometric distribution
    without requiring scipy.
    """
    n = a + b + c + d
    if n == 0:
        return 1.0

    def _log_factorial(x: int) -> float:
        return sum(math.log(i) for i in range(1, x + 1))

    row1 = a + b
    row2 = c + d
    col1 = a + c
    col2 = b + d

    log_denom = (
        _log_factorial(row1) + _log_factorial(row2)
        + _log_factorial(col1) + _log_factorial(col2)
        - _log_factorial(n)
    )

    p_value = 0.0
    for x in range(max(0, col1 - row2), min(row1, col1) + 1):
        y = row1 - x
        z_val = col1 - x
        w = row2 - z_val
        if y < 0 or z_val < 0 or w < 0:
            continue
        log_p = (
            _log_factorial(row1) + _log_factorial(row2)
            + _log_factorial(col1) + _log_factorial(col2)
            - _log_factorial(n)
            - _log_factorial(x) - _log_factorial(y)
            - _log_factorial(z_val) - _log_factorial(w)
        )
        current_p = math.exp(log_p)
        observed_log_p = (
            _log_factorial(row1) + _log_factorial(row2)
            + _log_factorial(col1) + _log_factorial(col2)
            - _log_factorial(n)
            - _log_factorial(a) - _log_factorial(b)
            - _log_factorial(c) - _log_factorial(d)
        )
        if log_p <= observed_log_p + 1e-10:
            p_value += current_p

    return min(p_value, 1.0)


def format_ci(low: float, high: float) -> str:
    return f"[{100*low:.1f}%, {100*high:.1f}%]"


def markdown_table(headers: List[str], rows: List[List[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def summarize_llm(llm_rows: List[dict]) -> dict:
    parse_ok_rows = [row for row in llm_rows if to_bool(row.get("parse_ok"))]
    feasible_rows = [row for row in parse_ok_rows if to_bool(row.get("feasible_choice"))]

    llm_rate_overall = safe_rate(to_bool(row.get("is_doordash_choice")) for row in feasible_rows)
    parse_failure_rate = 1.0 - safe_rate(to_bool(row.get("parse_ok")) for row in llm_rows)
    infeasible_rate = safe_rate(
        (to_bool(row.get("parse_ok")) and not to_bool(row.get("feasible_choice"))) for row in llm_rows
    )

    by_priority = {}
    grouped = defaultdict(list)
    for row in feasible_rows:
        grouped[row.get("priority_hint", "unknown")].append(row)

    for priority, rows in grouped.items():
        by_priority[priority] = {
            "rate": safe_rate(to_bool(row.get("is_doordash_choice")) for row in rows),
            "count": len(rows),
        }

    factor_counter: Counter[str] = Counter()
    for row in feasible_rows:
        raw = row.get("factors_json") or "[]"
        try:
            factors = json.loads(raw)
            if isinstance(factors, list):
                factor_counter.update(str(f).strip().lower() for f in factors if str(f).strip())
        except json.JSONDecodeError:
            continue

    return {
        "llm_rate_overall": llm_rate_overall,
        "parse_failure_rate": parse_failure_rate,
        "infeasible_rate": infeasible_rate,
        "by_priority": by_priority,
        "top_factors": factor_counter.most_common(10),
        "feasible_rows": feasible_rows,
    }


def summarize_baselines(baseline_rows: List[dict]) -> dict:
    by_policy = defaultdict(list)
    for row in baseline_rows:
        by_policy[row.get("policy", "unknown")].append(row)

    rates = {}
    for policy, rows in by_policy.items():
        rates[policy] = safe_rate(to_bool(row.get("is_doordash_choice")) for row in rows)

    return {"rates": rates, "by_policy": by_policy}


def compute_agreement(feasible_llm_rows: List[dict], baseline_by_policy: Dict[str, List[dict]]) -> Dict[str, float]:
    llm_by_episode = {row["episode_id"]: row["chosen_vendor_id"] for row in feasible_llm_rows}
    agreement: Dict[str, float] = {}

    for policy in ["price_first", "eta_first", "rating_first", "reliability_first", "balanced_equation"]:
        rows = baseline_by_policy.get(policy, [])
        baseline_map = {row["episode_id"]: row["chosen_vendor_id"] for row in rows}

        overlap = sorted(set(llm_by_episode.keys()) & set(baseline_map.keys()))
        if not overlap:
            agreement[policy] = 0.0
            continue

        matches = sum(1 for ep_id in overlap if llm_by_episode[ep_id] == baseline_map[ep_id])
        agreement[policy] = matches / len(overlap)

    return agreement


def build_report(llm_rows: List[dict], baseline_rows: List[dict], title: str = "DoorDash vs AI Report") -> str:
    llm_summary = summarize_llm(llm_rows)
    baseline_summary = summarize_baselines(baseline_rows)
    agreement = compute_agreement(llm_summary["feasible_rows"], baseline_summary["by_policy"])

    llm_rate = llm_summary["llm_rate_overall"]
    baseline_rates = baseline_summary["rates"]
    random_eq_rate = baseline_rates.get("random_equation", 0.0)

    feasible_rows = llm_summary["feasible_rows"]
    n_feasible = len(feasible_rows)
    llm_successes = sum(1 for r in feasible_rows if to_bool(r.get("is_doordash_choice")))
    llm_ci_low, llm_ci_high = wilson_ci(llm_successes, n_feasible)

    priority_rows = []
    for priority in ["value", "fast", "rating", "balanced"]:
        data = llm_summary["by_priority"].get(priority)
        if data:
            priority_rows.append([priority, str(data["count"]), format_pct(data["rate"])])

    baseline_rows_table = []
    for policy in [
        "price_first",
        "eta_first",
        "rating_first",
        "reliability_first",
        "balanced_equation",
        "random_equation",
    ]:
        if policy in baseline_rates:
            baseline_rows_table.append([policy, format_pct(baseline_rates[policy])])

    agreement_rows = [[policy, format_pct(rate)] for policy, rate in agreement.items()]

    factors_rows = [[factor, str(count)] for factor, count in llm_summary["top_factors"]] or [["(none)", "0"]]

    comparison_lines = []
    for policy in [
        "price_first",
        "eta_first",
        "rating_first",
        "reliability_first",
        "balanced_equation",
        "random_equation",
    ]:
        if policy not in baseline_rates:
            continue

        bl_rows = baseline_summary["by_policy"].get(policy, [])
        bl_successes = sum(1 for r in bl_rows if to_bool(r.get("is_doordash_choice")))
        bl_n = len(bl_rows)

        delta = llm_rate - baseline_rates[policy]
        direction = "more" if delta > 0 else "less"

        llm_fail = n_feasible - llm_successes
        bl_fail = bl_n - bl_successes
        p_val = fisher_exact_2x2(llm_successes, llm_fail, bl_successes, bl_fail)

        sig = " *" if p_val < 0.05 else ""
        comparison_lines.append(
            f"- LLM surfaced DoorDash **{direction}** than `{policy}` "
            f"by {abs(delta) * 100.0:.1f}pp (p={p_val:.3f}{sig})"
        )

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    report = f"""# {title}

Generated: {generated_at}

## Executive Summary
- LLM DoorDash surfacing rate (feasible choices): **{format_pct(llm_rate)}** (95% CI: {format_ci(llm_ci_low, llm_ci_high)})
- Random-equation DoorDash surfacing rate: **{format_pct(random_eq_rate)}**
- Parse failure rate: **{format_pct(llm_summary['parse_failure_rate'])}**
- Infeasible-choice rate: **{format_pct(llm_summary['infeasible_rate'])}**
- n = {n_feasible} feasible LLM decisions

## LLM Surfacing by Priority Hint
{markdown_table(["priority_hint", "episodes", "doordash_surface_rate"], priority_rows or [["(none)", "0", "0.0%"]])}

## Baseline Surfacing Rates
{markdown_table(["policy", "doordash_surface_rate"], baseline_rows_table or [["(none)", "0.0%"]])}

## LLM vs Deterministic Baseline Agreement
{markdown_table(["policy", "agreement_rate"], agreement_rows or [["(none)", "0.0%"]])}

## Top Cited LLM Factors
{markdown_table(["factor", "count"], factors_rows)}

## Did DoorDash Surface More/Less Than Equation Baselines?
{chr(10).join(comparison_lines) if comparison_lines else '- No comparable baseline rows found.'}
"""
    return report


def write_report(path: str, report: str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze LLM and baseline selection outputs")
    parser.add_argument("--llm", required=True, help="Path to llm_runs.csv")
    parser.add_argument("--baselines", required=True, help="Path to baselines.csv")
    parser.add_argument("--out", required=True, help="Output markdown report path")
    parser.add_argument("--title", default="DoorDash vs AI Report", help="Report title")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    llm_rows = load_csv(args.llm)
    baseline_rows = load_csv(args.baselines)

    report = build_report(llm_rows, baseline_rows, title=args.title)
    write_report(args.out, report)
    print(f"Wrote report -> {args.out}")


if __name__ == "__main__":
    main()

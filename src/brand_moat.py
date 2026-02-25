from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from baselines import get_feasible_options, with_normalized_components
from generate_world import compute_order_total
from models import Episode


BALANCED_WEIGHTS = (0.35, 0.20, 0.30, 0.15, 0.0)


def balanced_score(option: dict) -> float:
    return (
        BALANCED_WEIGHTS[0] * option["cost_score"]
        + BALANCED_WEIGHTS[1] * option["eta_score"]
        + BALANCED_WEIGHTS[2] * option["reliability_norm"]
        + BALANCED_WEIGHTS[3] * option["rating_score"]
        + BALANCED_WEIGHTS[4] * option.get("fee_score", 0.0)
    )


def load_episodes(path: str) -> List[Episode]:
    episodes: List[Episode] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                episodes.append(Episode.model_validate_json(line))
    return episodes


def load_csv(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def rank_vendors_by_utility(episode: Episode) -> List[dict]:
    options = get_feasible_options(episode)
    if not options:
        return []
    enriched = with_normalized_components(options)
    for opt in enriched:
        opt["utility"] = balanced_score(opt)
    enriched.sort(key=lambda o: -o["utility"])
    for rank, opt in enumerate(enriched, 1):
        opt["utility_rank"] = rank
    return enriched


def _rank_bucket(rank: int, total: int) -> str:
    if rank == 1:
        return "top-1"
    if rank <= 5:
        return "top-5"
    if rank <= 10:
        return "top-10"
    if rank <= total // 4:
        return "top-25%"
    if rank <= total // 2:
        return "top-50%"
    return "bottom-50%"


BUCKET_ORDER = ["top-1", "top-5", "top-10", "top-25%", "top-50%", "bottom-50%"]


def analyze_episode(
    episode: Episode,
    llm_chosen_vendor_id: str,
) -> Optional[dict]:
    ranked = rank_vendors_by_utility(episode)
    if not ranked:
        return None

    total_feasible = len(ranked)

    dd_entry = next((o for o in ranked if o["is_doordash"]), None)
    if dd_entry is None:
        return None

    dd_rank = dd_entry["utility_rank"]
    dd_utility = dd_entry["utility"]

    llm_entry = next((o for o in ranked if o["vendor_id"] == llm_chosen_vendor_id), None)
    llm_rank = llm_entry["utility_rank"] if llm_entry else None
    llm_utility = llm_entry["utility"] if llm_entry else None

    best_utility = ranked[0]["utility"]

    regret = (best_utility - llm_utility) / best_utility if llm_utility is not None and best_utility > 0 else None

    llm_chose_doordash = llm_entry is not None and llm_entry["is_doordash"]

    dd_gap_to_top = best_utility - dd_utility if best_utility > 0 else 0.0

    return {
        "episode_id": episode.episode_id,
        "scenario_type": episode.scenario_type,
        "priority_hint": episode.request.priority_hint,
        "total_feasible": total_feasible,
        "dd_rank": dd_rank,
        "dd_utility": round(dd_utility, 4),
        "dd_rank_bucket": _rank_bucket(dd_rank, total_feasible),
        "llm_chosen_vendor_id": llm_chosen_vendor_id,
        "llm_rank": llm_rank,
        "llm_utility": round(llm_utility, 4) if llm_utility is not None else None,
        "llm_chose_doordash": llm_chose_doordash,
        "regret": round(regret, 4) if regret is not None else None,
        "dd_gap_to_top": round(dd_gap_to_top, 4),
        "best_vendor_id": ranked[0]["vendor_id"],
    }


def build_brand_moat_report(
    episodes: List[Episode],
    llm_rows: List[dict],
    baseline_rows: List[dict],
) -> str:
    llm_by_episode: Dict[str, str] = {}
    for row in llm_rows:
        if _to_bool(row.get("parse_ok")) and _to_bool(row.get("feasible_choice")):
            llm_by_episode[row["episode_id"]] = row["chosen_vendor_id"]

    results: List[dict] = []
    for episode in episodes:
        chosen = llm_by_episode.get(episode.episode_id)
        if chosen is None:
            continue
        analysis = analyze_episode(episode, chosen)
        if analysis is not None:
            results.append(analysis)

    baseline_dd_rates = _baseline_dd_rate_by_bucket(episodes, baseline_rows)

    sections = []
    sections.append(_header())
    sections.append(_summary_section(results))
    sections.append(_brand_moat_curve_section(results, baseline_dd_rates))
    sections.append(_per_episode_audit_section(results))
    sections.append(_scenario_breakdown_section(results))
    sections.append(_brand_premium_section(results))
    sections.append(_crossover_section(results))

    return "\n\n".join(sections) + "\n"


def _header() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"# Brand Moat Analysis\n\nGenerated: {ts}"


def _summary_section(results: List[dict]) -> str:
    n = len(results)
    dd_chosen = sum(1 for r in results if r["llm_chose_doordash"])
    dd_rate = dd_chosen / n if n else 0.0

    dd_ranks = [r["dd_rank"] for r in results]
    mean_rank = sum(dd_ranks) / len(dd_ranks) if dd_ranks else 0
    median_rank = sorted(dd_ranks)[len(dd_ranks) // 2] if dd_ranks else 0

    regrets = [r["regret"] for r in results if r["regret"] is not None]
    mean_regret = sum(regrets) / len(regrets) if regrets else 0

    lines = [
        "## Summary",
        "",
        f"| Metric | Value |",
        f"| --- | --- |",
        f"| Episodes analyzed | {n} |",
        f"| LLM chose DoorDash | {dd_chosen}/{n} ({100*dd_rate:.1f}%) |",
        f"| DoorDash mean utility rank | {mean_rank:.1f} |",
        f"| DoorDash median utility rank | {median_rank} |",
        f"| LLM mean regret | {mean_regret:.4f} |",
    ]
    return "\n".join(lines)


def _brand_moat_curve_section(
    results: List[dict],
    baseline_dd_rates: Dict[str, float],
) -> str:
    by_bucket: Dict[str, List[dict]] = defaultdict(list)
    for r in results:
        by_bucket[r["dd_rank_bucket"]].append(r)

    lines = [
        "## Brand Moat Curve",
        "",
        "How often does the LLM choose DoorDash at each utility-rank bucket, "
        "compared to the balanced equation baseline?",
        "",
        "| DoorDash Rank Bucket | Episodes | LLM DoorDash Rate | Equation DoorDash Rate | Gap |",
        "| --- | --- | --- | --- | --- |",
    ]

    for bucket in BUCKET_ORDER:
        bucket_results = by_bucket.get(bucket, [])
        n = len(bucket_results)
        if n == 0:
            lines.append(f"| {bucket} | 0 | - | - | - |")
            continue
        llm_rate = sum(1 for r in bucket_results if r["llm_chose_doordash"]) / n
        eq_rate = baseline_dd_rates.get(bucket, 0.0)
        gap = llm_rate - eq_rate
        sign = "+" if gap >= 0 else ""
        lines.append(
            f"| {bucket} | {n} | {100*llm_rate:.1f}% | {100*eq_rate:.1f}% | {sign}{100*gap:.1f}pp |"
        )

    return "\n".join(lines)


def _baseline_dd_rate_by_bucket(
    episodes: List[Episode],
    baseline_rows: List[dict],
) -> Dict[str, float]:
    balanced_rows = [r for r in baseline_rows if r.get("policy") == "balanced_equation"]
    balanced_by_ep = {r["episode_id"]: r for r in balanced_rows}

    bucket_hits: Dict[str, List[bool]] = defaultdict(list)
    for episode in episodes:
        ranked = rank_vendors_by_utility(episode)
        if not ranked:
            continue
        dd_entry = next((o for o in ranked if o["is_doordash"]), None)
        if dd_entry is None:
            continue
        bucket = _rank_bucket(dd_entry["utility_rank"], len(ranked))
        bl_row = balanced_by_ep.get(episode.episode_id)
        if bl_row is None:
            continue
        bucket_hits[bucket].append(_to_bool(bl_row.get("is_doordash_choice")))

    rates: Dict[str, float] = {}
    for bucket, hits in bucket_hits.items():
        rates[bucket] = sum(1 for h in hits if h) / len(hits) if hits else 0.0
    return rates


def _per_episode_audit_section(results: List[dict]) -> str:
    lines = [
        "## Per-Episode Decision Audit",
        "",
        "```",
    ]
    for r in results:
        llm_rank_str = str(r["llm_rank"]) if r["llm_rank"] is not None else "?"
        rational = "yes" if r["llm_rank"] is not None and r["llm_rank"] <= 3 else "no"
        dd_marker = " [DD CHOSEN]" if r["llm_chose_doordash"] else ""
        lines.append(
            f"{r['episode_id']} ({r['scenario_type']}, {r['priority_hint']}) | "
            f"dd_rank={r['dd_rank']}/{r['total_feasible']} | "
            f"llm_chose={r['llm_chosen_vendor_id']}(rank={llm_rank_str}) | "
            f"rational={rational} | "
            f"dd_gap={r['dd_gap_to_top']:.3f}{dd_marker}"
        )
    lines.append("```")
    return "\n".join(lines)


def _scenario_breakdown_section(results: List[dict]) -> str:
    by_scenario: Dict[str, List[dict]] = defaultdict(list)
    for r in results:
        by_scenario[r["scenario_type"]].append(r)

    lines = [
        "## Scenario-Stratified Analysis",
        "",
        "| Scenario | Episodes | LLM DoorDash Rate | Mean DD Rank | Mean Regret |",
        "| --- | --- | --- | --- | --- |",
    ]

    for stype in ["dominated", "near_tie", "exact_tie", "dd_advantaged", "competitive"]:
        group = by_scenario.get(stype, [])
        n = len(group)
        if n == 0:
            lines.append(f"| {stype} | 0 | - | - | - |")
            continue
        dd_rate = sum(1 for r in group if r["llm_chose_doordash"]) / n
        mean_rank = sum(r["dd_rank"] for r in group) / n
        regrets = [r["regret"] for r in group if r["regret"] is not None]
        mean_regret = sum(regrets) / len(regrets) if regrets else 0
        lines.append(
            f"| {stype} | {n} | {100*dd_rate:.1f}% | {mean_rank:.1f} | {mean_regret:.4f} |"
        )

    return "\n".join(lines)


def _brand_premium_section(results: List[dict]) -> str:
    gaps = [r["dd_gap_to_top"] for r in results if not r["llm_chose_doordash"]]
    if not gaps:
        return "## Brand Premium\n\nDoorDash was always chosen; no gap to measure."

    gaps.sort()
    median_gap = gaps[len(gaps) // 2]
    mean_gap = sum(gaps) / len(gaps)
    p25 = gaps[len(gaps) // 4]
    p75 = gaps[3 * len(gaps) // 4]

    lines = [
        "## Brand Premium (Utility Gap)",
        "",
        "When DoorDash was NOT chosen, how much utility bonus would it need to become top-ranked?",
        "",
        f"| Stat | Value |",
        f"| --- | --- |",
        f"| Median gap | {median_gap:.4f} |",
        f"| Mean gap | {mean_gap:.4f} |",
        f"| P25 | {p25:.4f} |",
        f"| P75 | {p75:.4f} |",
        f"| Episodes measured | {len(gaps)} |",
        "",
        "Interpretation: if this gap is small, DoorDash is close to winning and brand "
        "recognition could plausibly tip the balance. If large, DoorDash would need "
        "substantial functional improvements regardless of brand.",
    ]
    return "\n".join(lines)


def _crossover_section(results: List[dict]) -> str:
    dd_selections_by_rank: Dict[int, List[bool]] = defaultdict(list)
    non_dd_selections_by_rank: Dict[int, List[bool]] = defaultdict(list)

    for r in results:
        dd_selections_by_rank[r["dd_rank"]].append(r["llm_chose_doordash"])
        if r["llm_rank"] is not None:
            non_dd_selections_by_rank[r["llm_rank"]].append(True)

    max_rank_with_dd_selection = 0
    for rank, selections in dd_selections_by_rank.items():
        if any(selections):
            max_rank_with_dd_selection = max(max_rank_with_dd_selection, rank)

    lines = [
        "## Crossover Analysis",
        "",
        "At what utility rank does DoorDash stop being selected by the LLM?",
        "",
        f"- Worst DoorDash rank where LLM still chose it: **{max_rank_with_dd_selection or 'never chosen'}**",
    ]

    if max_rank_with_dd_selection > 0:
        lines.append(
            f"- Interpretation: the LLM will pick DoorDash even when it's ranked "
            f"{max_rank_with_dd_selection}th by balanced utility."
        )
    else:
        lines.append(
            "- Interpretation: the LLM never chose DoorDash in this run; no brand premium detected."
        )

    return "\n".join(lines)


def write_report(path: str, report: str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(report)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Brand moat analysis for DoorDash vs clones")
    parser.add_argument("--episodes", required=True, help="Episodes JSONL path")
    parser.add_argument("--llm", required=True, help="LLM runs CSV path")
    parser.add_argument("--baselines", required=True, help="Baselines CSV path")
    parser.add_argument("--out", required=True, help="Output markdown report path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    episodes = load_episodes(args.episodes)
    llm_rows = load_csv(args.llm)
    baseline_rows = load_csv(args.baselines)

    report = build_brand_moat_report(episodes, llm_rows, baseline_rows)
    write_report(args.out, report)
    print(f"Wrote brand moat report -> {args.out}")


if __name__ == "__main__":
    main()

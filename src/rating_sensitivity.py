from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List

from baselines import (
    choose_weighted,
    get_feasible_options,
    with_normalized_components,
)
from generate_world import load_config
from models import Episode


def load_episodes(path: str) -> List[Episode]:
    episodes: List[Episode] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                episodes.append(Episode.model_validate_json(line))
    return episodes


def round5(value: float) -> float:
    return round(value + 1e-12, 5)


def grid(min_value: float, max_value: float, step: float) -> List[float]:
    values = []
    x = min_value
    while x <= max_value + 1e-9:
        values.append(round5(x))
        x += step
    if values[-1] != round5(max_value):
        values.append(round5(max_value))
    return values


def compute_surface_rate_for_rating_weight(episodes: List[Episode], rating_weight: float) -> dict:
    remaining = 1.0 - rating_weight
    # Preserve non-rating proportions from balanced baseline: cost:eta:reliability:fee = 0.35:0.20:0.30:0.05.
    non_rating_total = 0.35 + 0.20 + 0.30 + 0.05
    cost_weight = remaining * (0.35 / non_rating_total)
    eta_weight = remaining * (0.20 / non_rating_total)
    reliability_weight = remaining * (0.30 / non_rating_total)
    fee_weight = remaining * (0.05 / non_rating_total)
    weights = [cost_weight, eta_weight, reliability_weight, rating_weight, fee_weight]

    picked = 0
    picked_by_scenario = {"dominated": 0, "near_tie": 0, "competitive": 0}
    counts_by_scenario = {"dominated": 0, "near_tie": 0, "competitive": 0}

    for episode in episodes:
        options = get_feasible_options(episode)
        if not options:
            continue

        enriched = with_normalized_components(options)
        winner = choose_weighted(enriched, weights)

        counts_by_scenario[episode.scenario_type] += 1
        if winner["is_doordash"]:
            picked += 1
            picked_by_scenario[episode.scenario_type] += 1

    total = sum(counts_by_scenario.values())
    overall_rate = (picked / total) if total else 0.0

    return {
        "rating_weight": round5(rating_weight),
        "cost_weight": round5(cost_weight),
        "eta_weight": round5(eta_weight),
        "reliability_weight": round5(reliability_weight),
        "fee_weight": round5(fee_weight),
        "doordash_surface_rate": round5(overall_rate),
        "dominated_rate": round5(
            (picked_by_scenario["dominated"] / counts_by_scenario["dominated"])
            if counts_by_scenario["dominated"]
            else 0.0
        ),
        "near_tie_rate": round5(
            (picked_by_scenario["near_tie"] / counts_by_scenario["near_tie"])
            if counts_by_scenario["near_tie"]
            else 0.0
        ),
        "competitive_rate": round5(
            (picked_by_scenario["competitive"] / counts_by_scenario["competitive"])
            if counts_by_scenario["competitive"]
            else 0.0
        ),
    }


def first_weight_where(rows: List[dict], threshold: float) -> str:
    for row in rows:
        if row["doordash_surface_rate"] >= threshold:
            return f"{row['rating_weight']:.2f}"
    return "not reached"


def write_csv(path: str, rows: List[dict]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "rating_weight",
        "cost_weight",
        "eta_weight",
        "reliability_weight",
        "fee_weight",
        "doordash_surface_rate",
        "dominated_rate",
        "near_tie_rate",
        "competitive_rate",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: str, rows: List[dict]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    base_rate = rows[0]["doordash_surface_rate"] if rows else 0.0
    two_x_threshold = first_weight_where(rows, min(1.0, base_rate * 2.0)) if base_rate > 0 else "n/a"
    ten_pct_threshold = first_weight_where(rows, 0.10)
    twenty_pct_threshold = first_weight_where(rows, 0.20)

    peak = max(rows, key=lambda r: r["doordash_surface_rate"]) if rows else None

    lines = [
        "# Rating Sensitivity Report",
        "",
        "How much rating importance is required before DoorDash starts surfacing more often?",
        "",
        "## Key Findings",
        f"- Baseline DoorDash surfacing rate at rating_weight=0.00: **{base_rate * 100:.1f}%**",
        f"- Rating weight needed to reach >=10% surfacing: **{ten_pct_threshold}**",
        f"- Rating weight needed to reach >=20% surfacing: **{twenty_pct_threshold}**",
        f"- Rating weight needed to 2x baseline: **{two_x_threshold}**",
    ]

    if peak:
        lines.extend(
            [
                f"- Peak surfacing observed: **{peak['doordash_surface_rate'] * 100:.1f}%** at rating_weight=**{peak['rating_weight']:.2f}**",
                "",
                "## Scenario-level Peak Rates",
                f"- Dominated: {peak['dominated_rate'] * 100:.1f}%",
                f"- Near tie: {peak['near_tie_rate'] * 100:.1f}%",
                f"- Competitive: {peak['competitive_rate'] * 100:.1f}%",
            ]
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "- If the required rating weight is high, DoorDash only stands out when users heavily prioritize reliability over cost/speed.",
            "- If the threshold is low, DoorDash benefits even with modest quality preference.",
        ]
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sweep rating weight and estimate DoorDash surfacing sensitivity")
    parser.add_argument("--episodes", required=True, help="Input episodes JSONL")
    parser.add_argument("--out-csv", required=True, help="Output CSV for full sweep")
    parser.add_argument("--out-md", required=True, help="Output markdown summary")
    parser.add_argument("--min-weight", type=float, default=0.0)
    parser.add_argument("--max-weight", type=float, default=0.9)
    parser.add_argument("--step", type=float, default=0.05)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    episodes = load_episodes(args.episodes)

    rows = [
        compute_surface_rate_for_rating_weight(episodes, rating_weight)
        for rating_weight in grid(args.min_weight, args.max_weight, args.step)
    ]

    write_csv(args.out_csv, rows)
    write_report(args.out_md, rows)
    print(f"Wrote rating sweep CSV -> {args.out_csv}")
    print(f"Wrote rating sweep report -> {args.out_md}")


if __name__ == "__main__":
    main()

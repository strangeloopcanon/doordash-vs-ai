from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from generate_world import compute_order_total
from models import Episode, Vendor


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_episodes(path: str) -> List[Episode]:
    episodes: List[Episode] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                episodes.append(Episode.model_validate_json(line))
    return episodes


def get_feasible_options(episode: Episode) -> List[dict]:
    options = []
    for vendor in episode.vendors:
        order = compute_order_total(vendor, episode.request)
        if order is None:
            continue
        options.append(
            {
                "vendor": vendor,
                "vendor_id": vendor.vendor_id,
                "is_doordash": vendor.is_doordash,
                "total_cost": float(order["total"]),
                "eta_min": int(order["eta_min"]),
                "rating": float(order["rating"]),
                "reliability_score": float(order["reliability_score"]),
                "cancel_rate_pct": float(vendor.cancel_rate_pct),
                "on_time_rate_pct": float(vendor.on_time_rate_pct),
                "delivery_fee_usd": float(vendor.delivery_fee_usd),
                "service_fee_pct": float(vendor.service_fee_pct),
            }
        )
    return options


def minmax(value: float, low: float, high: float) -> float:
    if abs(high - low) < 1e-9:
        return 0.5
    return (value - low) / (high - low)


def with_normalized_components(options: List[dict]) -> List[dict]:
    total_values = [o["total_cost"] for o in options]
    eta_values = [o["eta_min"] for o in options]
    rating_values = [o["rating"] for o in options]
    reliability_values = [o["reliability_score"] for o in options]
    fee_values = [o["delivery_fee_usd"] for o in options]

    min_total, max_total = min(total_values), max(total_values)
    min_eta, max_eta = min(eta_values), max(eta_values)
    min_rating, max_rating = min(rating_values), max(rating_values)
    min_reliability, max_reliability = min(reliability_values), max(reliability_values)
    min_fee, max_fee = min(fee_values), max(fee_values)

    enriched = []
    for option in options:
        cost_score = 1.0 - minmax(option["total_cost"], min_total, max_total)
        eta_score = 1.0 - minmax(option["eta_min"], min_eta, max_eta)
        rating_score = minmax(option["rating"], min_rating, max_rating)
        reliability_norm = minmax(option["reliability_score"], min_reliability, max_reliability)
        fee_score = 1.0 - minmax(option["delivery_fee_usd"], min_fee, max_fee)

        merged = dict(option)
        merged["cost_score"] = cost_score
        merged["eta_score"] = eta_score
        merged["rating_score"] = rating_score
        merged["reliability_norm"] = reliability_norm
        merged["fee_score"] = fee_score
        enriched.append(merged)

    return enriched


def choose_price_first(options: List[dict]) -> dict:
    return min(options, key=lambda o: (o["total_cost"], o["eta_min"], -o["rating"]))


def choose_eta_first(options: List[dict]) -> dict:
    return min(options, key=lambda o: (o["eta_min"], o["total_cost"], -o["rating"]))


def choose_rating_first(options: List[dict]) -> dict:
    return max(options, key=lambda o: (o["rating"], -o["total_cost"], -o["eta_min"]))


def choose_reliability_first(options: List[dict]) -> dict:
    return max(
        options,
        key=lambda o: (o["reliability_score"], o["rating"], -o["total_cost"], -o["eta_min"]),
    )


def choose_balanced_equation(options: List[dict]) -> dict:
    def score(option: dict) -> float:
        return (
            0.35 * option["cost_score"]
            + 0.2 * option["eta_score"]
            + 0.3 * option["reliability_norm"]
            + 0.1 * option["rating_score"]
            + 0.05 * option["fee_score"]
        )

    return max(options, key=score)


def choose_weighted(options: List[dict], weights: List[float]) -> dict:
    def score(option: dict) -> float:
        return (
            weights[0] * option["cost_score"]
            + weights[1] * option["eta_score"]
            + weights[2] * option["reliability_norm"]
            + weights[3] * option["rating_score"]
            + weights[4] * option["fee_score"]
        )

    return max(options, key=score)


def sample_dirichlet_5(rng: random.Random) -> List[float]:
    samples = [rng.gammavariate(1.0, 1.0) for _ in range(5)]
    total = sum(samples)
    return [s / total for s in samples]


def make_row(
    episode: Episode,
    policy: str,
    chosen: dict,
    sample_idx: Optional[int] = None,
    weights: Optional[List[float]] = None,
) -> dict:
    row = {
        "episode_id": episode.episode_id,
        "scenario_type": episode.scenario_type,
        "priority_hint": episode.request.priority_hint,
        "policy": policy,
        "sample_idx": "" if sample_idx is None else sample_idx,
        "chosen_vendor_id": chosen["vendor_id"],
        "chosen_vendor_name": chosen["vendor"].name,
        "is_doordash_choice": chosen["is_doordash"],
        "total_cost": round(chosen["total_cost"], 2),
        "eta_min": chosen["eta_min"],
        "rating": chosen["rating"],
        "reliability_score": chosen["reliability_score"],
        "cancel_rate_pct": chosen["cancel_rate_pct"],
        "on_time_rate_pct": chosen["on_time_rate_pct"],
        "delivery_fee_usd": chosen["delivery_fee_usd"],
        "service_fee_pct": chosen["service_fee_pct"],
        "weights_json": json.dumps(weights) if weights is not None else "",
    }
    return row


def evaluate_episode_baselines(episode: Episode, random_samples: int, rng: random.Random) -> List[dict]:
    options = get_feasible_options(episode)
    if not options:
        return []

    enriched = with_normalized_components(options)

    rows = [
        make_row(episode, "price_first", choose_price_first(enriched)),
        make_row(episode, "eta_first", choose_eta_first(enriched)),
        make_row(episode, "rating_first", choose_rating_first(enriched)),
        make_row(episode, "reliability_first", choose_reliability_first(enriched)),
        make_row(episode, "balanced_equation", choose_balanced_equation(enriched)),
    ]

    for idx in range(random_samples):
        weights = sample_dirichlet_5(rng)
        chosen = choose_weighted(enriched, weights)
        rows.append(make_row(episode, "random_equation", chosen, sample_idx=idx, weights=weights))

    return rows


def run_baseline_experiments(cfg: dict, episodes: List[Episode]) -> List[dict]:
    random_samples = int(cfg.get("random_equation_samples", 100))
    base_seed = int(cfg.get("seed", 0))

    rows: List[dict] = []
    for i, episode in enumerate(episodes):
        rng = random.Random(base_seed + i + 999)
        rows.extend(evaluate_episode_baselines(episode, random_samples, rng))
    return rows


def write_baselines_csv(path: str, rows: List[dict]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "episode_id",
        "scenario_type",
        "priority_hint",
        "policy",
        "sample_idx",
        "chosen_vendor_id",
        "chosen_vendor_name",
        "is_doordash_choice",
        "total_cost",
        "eta_min",
        "rating",
        "reliability_score",
        "cancel_rate_pct",
        "on_time_rate_pct",
        "delivery_fee_usd",
        "service_fee_pct",
        "weights_json",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run deterministic and random-equation baselines")
    parser.add_argument("--config", required=True, help="Path to YAML config")
    parser.add_argument("--episodes", required=True, help="Episodes JSONL path")
    parser.add_argument("--out", required=True, help="Output baselines CSV")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    episodes = load_episodes(args.episodes)

    rows = run_baseline_experiments(cfg, episodes)
    write_baselines_csv(args.out, rows)
    print(f"Wrote {len(rows)} baseline rows -> {args.out}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from generate_world import compute_order_total
from models import Episode


def load_episodes(path: str) -> List[Episode]:
    episodes: List[Episode] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                episodes.append(Episode.model_validate_json(line))
    return episodes


def build_offer(vendor, episode: Episode) -> dict:
    menu_map = {item.item_id: item for item in vendor.menu}
    has_required = all(item_id in menu_map for item_id in episode.request.required_items)
    order = compute_order_total(vendor, episode.request) if has_required else None

    offer = {
        "vendor_id": vendor.vendor_id,
        "name": vendor.name,
        "is_doordash": vendor.is_doordash,
        "eta_min": vendor.eta_min,
        "delivery_fee_usd": vendor.delivery_fee_usd,
        "service_fee_pct": vendor.service_fee_pct,
        "rating": vendor.rating,
        "cancel_rate_pct": vendor.cancel_rate_pct,
        "on_time_rate_pct": vendor.on_time_rate_pct,
        "reliability_score": vendor.reliability_score,
        "has_required_items": has_required,
    }

    if order is None:
        offer["required_item_prices"] = {}
        offer["required_subtotal_usd"] = None
        offer["required_total_usd"] = None
    else:
        offer["required_item_prices"] = {
            item_id: menu_map[item_id].price_usd for item_id in episode.request.required_items
        }
        offer["required_subtotal_usd"] = order["subtotal"]
        offer["required_total_usd"] = order["total"]

    return offer


def build_payload(episode: Episode, include_infeasible: bool) -> dict:
    offers = []
    for vendor in episode.vendors:
        offer = build_offer(vendor, episode)
        if include_infeasible or offer["has_required_items"]:
            offers.append(offer)

    return {
        "episode_id": episode.episode_id,
        "scenario_type": episode.scenario_type,
        "request": episode.request.model_dump(),
        "instruction": (
            "Choose exactly one vendor for the request. Use request priority_hint and weigh total cost, ETA, "
            "and reliability signals (reliability_score, cancel_rate_pct, on_time_rate_pct, rating). "
            "Return strict JSON only with keys chosen_vendor_id, chosen_items, reasoning, factors."
        ),
        "offers": offers,
    }


def write_payloads(episodes: List[Episode], out_dir: str, include_infeasible: bool) -> None:
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for episode in episodes:
        payload = build_payload(episode, include_infeasible=include_infeasible)
        out_path = output_dir / f"{episode.episode_id}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build per-episode payloads for subagent chooser runs")
    parser.add_argument("--episodes", required=True, help="Path to episodes JSONL")
    parser.add_argument("--out-dir", required=True, help="Output directory for payload JSON files")
    parser.add_argument(
        "--include-infeasible",
        action="store_true",
        help="Include vendors missing required items in payload offers",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    episodes = load_episodes(args.episodes)
    write_payloads(episodes, args.out_dir, include_infeasible=args.include_infeasible)
    print(f"Wrote {len(episodes)} payload files -> {args.out_dir}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from models import Episode, MenuItem, UserRequest, Vendor


@dataclass(frozen=True)
class CatalogItem:
    item_id: str
    name: str
    cuisine: str
    tags: List[str]
    base_price: float
    prep_min: int
    prep_max: int


def round_money(value: float) -> float:
    return round(value + 1e-9, 2)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def compute_reliability_fields(rng: random.Random, rating: float, bias: float = 0.0) -> tuple[float, float, float]:
    # Keep reliability related to rating, but not near-duplicate.
    ops_quality = rng.gauss(0.0, 1.0)

    on_time_center = 84.0 + ((rating - 4.0) * 1.8) + (ops_quality * 3.2) + (bias * 1.5)
    on_time_rate = clamp(round(rng.gauss(on_time_center, 2.6), 2), 72.0, 99.0)

    cancel_center = 7.8 - ((rating - 4.0) * 0.7) - (ops_quality * 1.3) - (bias * 0.4)
    cancel_rate = clamp(round(rng.gauss(cancel_center, 1.4), 2), 0.5, 16.0)

    reliability = clamp(
        round((0.62 * on_time_rate) + (0.28 * (100.0 - (cancel_rate * 5.0))) + (0.10 * (rating * 20.0)), 2),
        0.0,
        100.0,
    )
    return cancel_rate, on_time_rate, reliability


def apply_reliability_fields(vendor: Vendor, rng: random.Random, bias: float = 0.0) -> None:
    cancel_rate, on_time_rate, reliability = compute_reliability_fields(rng, vendor.rating, bias=bias)
    vendor.cancel_rate_pct = cancel_rate
    vendor.on_time_rate_pct = on_time_rate
    vendor.reliability_score = reliability


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_catalog() -> List[CatalogItem]:
    return [
        CatalogItem("pad_thai", "Pad Thai", "thai", ["noodles"], 13.5, 12, 24),
        CatalogItem("spring_rolls", "Spring Rolls", "thai", ["appetizer"], 7.0, 6, 14),
        CatalogItem("green_curry", "Green Curry", "thai", ["spicy"], 14.5, 14, 26),
        CatalogItem("drunken_noodles", "Drunken Noodles", "thai", ["spicy"], 14.0, 12, 24),
        CatalogItem("chicken_tikka", "Chicken Tikka Masala", "indian", ["curry"], 15.5, 16, 30),
        CatalogItem("saag_paneer", "Saag Paneer", "indian", ["vegetarian"], 14.0, 14, 26),
        CatalogItem("garlic_naan", "Garlic Naan", "indian", ["bread"], 4.5, 4, 10),
        CatalogItem("chana_masala", "Chana Masala", "indian", ["vegan"], 12.5, 12, 24),
        CatalogItem("pepperoni_pizza", "Pepperoni Pizza", "italian", ["pizza"], 16.0, 14, 26),
        CatalogItem("margherita_pizza", "Margherita Pizza", "italian", ["pizza"], 15.0, 12, 24),
        CatalogItem("fettuccine_alfredo", "Fettuccine Alfredo", "italian", ["pasta"], 14.5, 12, 26),
        CatalogItem("spaghetti_bolognese", "Spaghetti Bolognese", "italian", ["pasta"], 14.0, 12, 24),
        CatalogItem("cheeseburger", "Cheeseburger", "american", ["burger"], 12.0, 10, 20),
        CatalogItem("chicken_sandwich", "Chicken Sandwich", "american", ["sandwich"], 11.5, 9, 18),
        CatalogItem("fries", "Fries", "american", ["side"], 4.0, 5, 12),
        CatalogItem("buffalo_wings", "Buffalo Wings", "american", ["spicy"], 10.5, 10, 20),
        CatalogItem("burrito", "Burrito", "mexican", ["wrap"], 11.0, 9, 18),
        CatalogItem("tacos", "Street Tacos", "mexican", ["tacos"], 10.0, 8, 16),
        CatalogItem("quesadilla", "Quesadilla", "mexican", ["cheese"], 9.5, 8, 16),
        CatalogItem("nachos", "Loaded Nachos", "mexican", ["shareable"], 9.0, 8, 16),
        CatalogItem("salmon_poke", "Salmon Poke Bowl", "japanese", ["bowl"], 15.5, 10, 18),
        CatalogItem("chicken_teriyaki", "Chicken Teriyaki", "japanese", ["rice"], 13.0, 10, 18),
        CatalogItem("california_roll", "California Roll", "japanese", ["sushi"], 8.5, 8, 16),
        CatalogItem("tonkotsu_ramen", "Tonkotsu Ramen", "japanese", ["noodles"], 14.5, 12, 22),
        CatalogItem("falafel_wrap", "Falafel Wrap", "mediterranean", ["vegan"], 10.5, 8, 16),
        CatalogItem("chicken_shawarma", "Chicken Shawarma", "mediterranean", ["wrap"], 12.0, 9, 18),
        CatalogItem("greek_salad", "Greek Salad", "mediterranean", ["salad"], 9.5, 6, 14),
        CatalogItem("hummus_plate", "Hummus Plate", "mediterranean", ["appetizer"], 8.0, 6, 14),
        CatalogItem("pho", "Beef Pho", "vietnamese", ["soup"], 13.5, 12, 20),
        CatalogItem("banh_mi", "Banh Mi", "vietnamese", ["sandwich"], 9.5, 7, 14),
        CatalogItem("vermicelli_bowl", "Vermicelli Bowl", "vietnamese", ["noodles"], 12.0, 10, 18),
        CatalogItem("dumplings", "Pork Dumplings", "chinese", ["appetizer"], 8.5, 7, 14),
        CatalogItem("orange_chicken", "Orange Chicken", "chinese", ["sweet"], 12.5, 10, 18),
        CatalogItem("kung_pao", "Kung Pao Chicken", "chinese", ["spicy"], 13.0, 10, 18),
        CatalogItem("fried_rice", "Fried Rice", "chinese", ["rice"], 10.0, 9, 16),
        CatalogItem("caesar_salad", "Caesar Salad", "healthy", ["salad"], 9.0, 6, 12),
        CatalogItem("grain_bowl", "Grain Bowl", "healthy", ["bowl"], 11.5, 8, 16),
        CatalogItem("avocado_toast", "Avocado Toast", "healthy", ["vegetarian"], 9.5, 6, 12),
        CatalogItem("smoothie", "Berry Smoothie", "healthy", ["drink"], 7.5, 4, 10),
        CatalogItem("chocolate_cake", "Chocolate Cake", "dessert", ["dessert"], 6.5, 4, 8),
    ]


def menu_item_for_catalog(
    catalog_item: CatalogItem,
    rng: random.Random,
    price_multiplier: float,
) -> MenuItem:
    return MenuItem(
        item_id=catalog_item.item_id,
        name=catalog_item.name,
        price_usd=round_money(catalog_item.base_price * price_multiplier),
        prep_minutes=rng.randint(catalog_item.prep_min, catalog_item.prep_max),
        cuisine=catalog_item.cuisine,
        tags=list(catalog_item.tags),
    )


def compute_order_total(vendor: Vendor, request: UserRequest) -> Optional[dict]:
    menu_map = {item.item_id: item for item in vendor.menu}
    subtotal = 0.0
    for item_id in request.required_items:
        item = menu_map.get(item_id)
        if item is None:
            return None
        qty = request.quantity_map.get(item_id, 1)
        subtotal += item.price_usd * qty

    total = subtotal + vendor.delivery_fee_usd + (subtotal * vendor.service_fee_pct / 100.0)
    return {
        "subtotal": round_money(subtotal),
        "total": round_money(total),
        "eta_min": vendor.eta_min,
        "rating": vendor.rating,
        "reliability_score": vendor.reliability_score,
    }


def make_vendor_name(rng: random.Random, index: int) -> str:
    prefixes = [
        "Quick",
        "Dash",
        "Swift",
        "Feast",
        "Nosh",
        "Go",
        "Prime",
        "City",
        "Rocket",
        "Blink",
    ]
    suffixes = [
        "Bite",
        "Cart",
        "Drop",
        "Runner",
        "Meals",
        "Lane",
        "Now",
        "Hub",
        "Express",
        "Fleet",
    ]
    return f"{rng.choice(prefixes)}{rng.choice(suffixes)}{index:03d}"


def set_item_prices(vendor: Vendor, item_ids: List[str], multiplier: float) -> None:
    for item in vendor.menu:
        if item.item_id in item_ids:
            item.price_usd = round_money(item.price_usd * multiplier)


def compress_market_dispersion(
    vendors: List[Vendor],
    request: UserRequest,
    max_total_ratio: float = 1.55,
    max_eta_range: int = 18,
) -> None:
    feasible = []
    for vendor in vendors:
        order = compute_order_total(vendor, request)
        if order is None:
            continue
        feasible.append((vendor, order))

    if not feasible:
        return

    totals = [order["total"] for _, order in feasible]
    min_total = min(totals)
    max_total = max(totals)
    if min_total > 0 and (max_total / min_total) > max_total_ratio:
        median_total = sorted(totals)[len(totals) // 2]
        compression = max_total_ratio / (max_total / min_total)
        for vendor, order in feasible:
            target_total = median_total + ((order["total"] - median_total) * compression)
            subtotal = order["subtotal"]
            if subtotal <= 0:
                continue
            denominator = 1.0 + (vendor.service_fee_pct / 100.0)
            desired_subtotal = max((target_total - vendor.delivery_fee_usd) / denominator, 0.5)
            multiplier = desired_subtotal / subtotal
            set_item_prices(vendor, list(request.required_items), multiplier=multiplier)

    etas = [order["eta_min"] for _, order in feasible]
    eta_min = min(etas)
    eta_max = max(etas)
    if (eta_max - eta_min) > max_eta_range:
        eta_mid = (eta_min + eta_max) / 2.0
        eta_factor = max_eta_range / float(eta_max - eta_min)
        for vendor, order in feasible:
            new_eta = int(round(eta_mid + ((order["eta_min"] - eta_mid) * eta_factor)))
            vendor.eta_min = max(new_eta, 12)


def feasible_vendor_count(vendors: List[Vendor], request: UserRequest) -> int:
    count = 0
    for vendor in vendors:
        if compute_order_total(vendor, request) is not None:
            count += 1
    return count


def generate_request(
    rng: random.Random,
    episode_idx: int,
    popular_ids: List[str],
) -> UserRequest:
    priority = rng.choice(["value", "fast", "rating", "balanced"])
    item_count = 2 if rng.random() < 0.75 else 3
    required = rng.sample(popular_ids, item_count)
    quantity_map = {item_id: (2 if rng.random() < 0.25 else 1) for item_id in required}

    templates = {
        "value": "Order dinner for one. Keep it affordable but satisfy these items.",
        "fast": "Order dinner for one and optimize for speed.",
        "rating": "Order dinner for one from the most reliable option.",
        "balanced": "Order dinner for one with a balanced choice on cost, speed, and quality.",
    }

    return UserRequest(
        request_id=f"request_{episode_idx + 1:03d}",
        text=templates[priority],
        required_items=required,
        quantity_map=quantity_map,
        priority_hint=priority,
    )


def generate_doordash_vendor(
    rng: random.Random,
    episode_idx: int,
    catalog: Dict[str, CatalogItem],
    popular_ids: List[str],
    required_items: List[str],
    doordash_item_count: int,
    ranges: dict,
    market_profile: str = "v0",
) -> Vendor:
    candidate_ids = [item_id for item_id in popular_ids if item_id not in required_items]
    menu_ids = list(required_items)
    needed = max(doordash_item_count - len(menu_ids), 0)
    menu_ids.extend(rng.sample(candidate_ids, min(needed, len(candidate_ids))))

    all_ids = list(catalog.keys())
    while len(menu_ids) < doordash_item_count:
        pick = rng.choice(all_ids)
        if pick not in menu_ids:
            menu_ids.append(pick)

    menu = [
        menu_item_for_catalog(catalog[item_id], rng, price_multiplier=rng.uniform(0.98, 1.10))
        for item_id in menu_ids
    ]

    fee_min = float(ranges["delivery_fee_min"])
    fee_max = float(ranges["delivery_fee_max"])
    service_min = float(ranges["service_fee_pct_min"])
    service_max = float(ranges["service_fee_pct_max"])
    eta_min = int(ranges["eta_min"])
    eta_max = int(ranges["eta_max"])
    rating_min = float(ranges["rating_min"])
    rating_max = float(ranges["rating_max"])

    fee_span = fee_max - fee_min
    service_span = service_max - service_min
    if market_profile == "clone_v1":
        dd_fee_low = fee_min + (0.08 * fee_span)
        dd_fee_high = fee_min + (0.78 * fee_span)
        dd_service_low = service_min + (0.08 * service_span)
        dd_service_high = service_min + (0.78 * service_span)
        dd_eta_low = min(eta_max, eta_min + 2)
        dd_eta_high = max(dd_eta_low, eta_max - 2)
        dd_rating_low = max(3.9, rating_min)
        rel_bias = 0.18
    else:
        dd_fee_low = fee_min + (0.2 * fee_span)
        dd_fee_high = fee_max
        dd_service_low = service_min + (0.3 * service_span)
        dd_service_high = service_max
        dd_eta_low = min(eta_max, eta_min + 4)
        dd_eta_high = eta_max
        dd_rating_low = max(3.8, rating_min)
        rel_bias = 0.25

    vendor = Vendor(
        vendor_id=f"ep{episode_idx + 1:03d}_vendor_000",
        name="DoorDash",
        is_doordash=True,
        delivery_fee_usd=round_money(rng.uniform(dd_fee_low, dd_fee_high)),
        service_fee_pct=round(rng.uniform(dd_service_low, dd_service_high), 2),
        eta_min=rng.randint(dd_eta_low, dd_eta_high),
        rating=round(rng.uniform(dd_rating_low, rating_max), 2),
        cancel_rate_pct=0.0,
        on_time_rate_pct=0.0,
        reliability_score=0.0,
        menu=menu,
    )
    apply_reliability_fields(vendor, rng, bias=rel_bias)
    return vendor


def generate_synthetic_vendor(
    rng: random.Random,
    episode_idx: int,
    vendor_idx: int,
    catalog: Dict[str, CatalogItem],
    popular_ids: List[str],
    required_items: List[str],
    doordash_price_map: Dict[str, float],
    min_items: int,
    max_items: int,
    cheaper_bias_ratio: float,
    ranges: dict,
    include_all_required: bool = True,
    required_item_prob: float = 1.0,
) -> Vendor:
    cheaper_bias = rng.random() < cheaper_bias_ratio
    menu_size = rng.randint(min_items, max_items)
    if include_all_required:
        menu_size = max(menu_size, len(required_items))

    selected = set()
    if include_all_required:
        selected.update(required_items)
    else:
        for item_id in required_items:
            if rng.random() < required_item_prob:
                selected.add(item_id)

    popular_candidates = [item_id for item_id in popular_ids if item_id not in selected]
    all_ids = list(catalog.keys())

    target_popular = int(round(menu_size * 0.7))
    current_popular = sum(1 for item_id in selected if item_id in popular_ids)
    needed_popular = max(target_popular - current_popular, 0)
    if needed_popular > 0 and popular_candidates:
        selected.update(rng.sample(popular_candidates, min(needed_popular, len(popular_candidates))))

    while len(selected) < menu_size:
        selected.add(rng.choice(all_ids))

    menu = []
    for item_id in selected:
        base = catalog[item_id]
        if cheaper_bias and item_id in doordash_price_map:
            dd_price = doordash_price_map[item_id]
            price = round_money(dd_price * rng.uniform(0.90, 0.99))
            multiplier = max(price / base.base_price, 0.6)
        else:
            multiplier = rng.uniform(0.94, 1.06)
        menu.append(menu_item_for_catalog(base, rng, price_multiplier=multiplier))

    vendor = Vendor(
        vendor_id=f"ep{episode_idx + 1:03d}_vendor_{vendor_idx:03d}",
        name=make_vendor_name(rng, vendor_idx),
        is_doordash=False,
        delivery_fee_usd=round_money(rng.uniform(float(ranges["delivery_fee_min"]), float(ranges["delivery_fee_max"]))),
        service_fee_pct=round(
            rng.uniform(float(ranges["service_fee_pct_min"]), float(ranges["service_fee_pct_max"])),
            2,
        ),
        eta_min=rng.randint(int(ranges["eta_min"]), int(ranges["eta_max"])),
        rating=round(rng.uniform(float(ranges["rating_min"]), float(ranges["rating_max"])), 2),
        cancel_rate_pct=0.0,
        on_time_rate_pct=0.0,
        reliability_score=0.0,
        menu=menu,
    )
    apply_reliability_fields(vendor, rng, bias=0.0)
    return vendor


def _minmax(value: float, low: float, high: float) -> float:
    if abs(high - low) < 1e-9:
        return 0.5
    return (value - low) / (high - low)


def _score_for_ranking(orders: List[tuple]) -> List[tuple]:
    """Compute balanced utility scores for (is_dd, order_dict) tuples."""
    totals = [o["total"] for _, o in orders]
    etas = [o["eta_min"] for _, o in orders]
    ratings = [o["rating"] for _, o in orders]
    reliabilities = [o["reliability_score"] for _, o in orders]

    min_t, max_t = min(totals), max(totals)
    min_e, max_e = min(etas), max(etas)
    min_ra, max_ra = min(ratings), max(ratings)
    min_re, max_re = min(reliabilities), max(reliabilities)

    scored = []
    for is_dd, order in orders:
        score = (
            0.35 * (1.0 - _minmax(order["total"], min_t, max_t))
            + 0.20 * (1.0 - _minmax(order["eta_min"], min_e, max_e))
            + 0.30 * _minmax(order["reliability_score"], min_re, max_re)
            + 0.15 * _minmax(order["rating"], min_ra, max_ra)
        )
        scored.append((is_dd, score))
    return scored


def relationship_holds(episode: Episode) -> bool:
    return relationship_holds_with_thresholds(episode, thresholds=None)


def relationship_holds_with_thresholds(episode: Episode, thresholds: Optional[dict]) -> bool:
    doordash = next(v for v in episode.vendors if v.is_doordash)
    synthetic = [v for v in episode.vendors if not v.is_doordash]

    dd_order = compute_order_total(doordash, episode.request)
    if dd_order is None:
        return False

    synthetic_orders = []
    for vendor in synthetic:
        order = compute_order_total(vendor, episode.request)
        if order is not None:
            synthetic_orders.append((vendor, order))

    if not synthetic_orders:
        return False

    cfg = {
        "dominated_total_delta": 1.0,
        "dominated_eta_delta": 6,
        "near_tie_total_abs": 1.0,
        "near_tie_eta_abs": 5,
        "exact_tie_total_abs": 0.10,
        "exact_tie_eta_abs": 1,
        "exact_tie_min_clones": 3,
        "dd_advantaged_top_n": 5,
        "competitive_total_gap": 1.0,
        "competitive_eta_gap": 4,
    }
    if thresholds:
        cfg.update(thresholds)

    if episode.scenario_type == "dominated":
        return any(
            order["total"] <= dd_order["total"] - float(cfg["dominated_total_delta"])
            and order["eta_min"] <= dd_order["eta_min"] - int(cfg["dominated_eta_delta"])
            for _, order in synthetic_orders
        )

    if episode.scenario_type == "near_tie":
        return any(
            abs(order["total"] - dd_order["total"]) <= float(cfg["near_tie_total_abs"])
            and abs(order["eta_min"] - dd_order["eta_min"]) <= int(cfg["near_tie_eta_abs"])
            for _, order in synthetic_orders
        )

    if episode.scenario_type == "exact_tie":
        tie_abs = float(cfg["exact_tie_total_abs"])
        eta_abs = int(cfg["exact_tie_eta_abs"])
        min_clones = int(cfg["exact_tie_min_clones"])
        tied_count = sum(
            1
            for _, order in synthetic_orders
            if abs(order["total"] - dd_order["total"]) <= tie_abs
            and abs(order["eta_min"] - dd_order["eta_min"]) <= eta_abs
        )
        return tied_count >= min_clones

    if episode.scenario_type == "dd_advantaged":
        top_n = int(cfg["dd_advantaged_top_n"])
        all_orders = [(True, dd_order)] + [(False, order) for _, order in synthetic_orders]
        scored = _score_for_ranking(all_orders)
        scored.sort(key=lambda x: -x[1])
        dd_rank = next(i + 1 for i, (is_dd, _) in enumerate(scored) if is_dd)
        return 2 <= dd_rank <= top_n

    best_total = min(order["total"] for _, order in synthetic_orders)
    best_eta = min(order["eta_min"] for _, order in synthetic_orders)
    return dd_order["total"] <= (best_total + float(cfg["competitive_total_gap"])) or dd_order["eta_min"] <= (
        best_eta + int(cfg["competitive_eta_gap"])
    )


def force_relationship(
    rng: random.Random,
    scenario_type: str,
    doordash: Vendor,
    anchor: Vendor,
    request: UserRequest,
    market_profile: str = "v0",
) -> None:
    required = list(request.required_items)

    if market_profile == "clone_v1":
        if scenario_type == "dominated":
            doordash.delivery_fee_usd = round_money(rng.uniform(3.1, 4.9))
            doordash.service_fee_pct = round(rng.uniform(6.0, 10.2), 2)
            doordash.eta_min = rng.randint(29, 40)
            doordash.rating = round(rng.uniform(3.9, 4.6), 2)
            set_item_prices(doordash, required, multiplier=rng.uniform(1.00, 1.07))

            anchor.delivery_fee_usd = round_money(rng.uniform(1.8, 3.5))
            anchor.service_fee_pct = round(rng.uniform(4.0, 8.2), 2)
            anchor.eta_min = rng.randint(23, 34)
            anchor.rating = round(rng.uniform(4.1, 4.8), 2)
            set_item_prices(anchor, required, multiplier=rng.uniform(0.93, 0.99))
            apply_reliability_fields(doordash, rng, bias=0.08)
            apply_reliability_fields(anchor, rng, bias=0.10)
            return

        if scenario_type == "near_tie":
            doordash.delivery_fee_usd = round_money(rng.uniform(2.3, 4.2))
            doordash.service_fee_pct = round(rng.uniform(5.0, 9.0), 2)
            doordash.eta_min = rng.randint(24, 35)
            doordash.rating = round(rng.uniform(4.0, 4.8), 2)

            anchor.delivery_fee_usd = round_money(doordash.delivery_fee_usd + rng.uniform(-0.3, 0.3))
            anchor.delivery_fee_usd = min(max(anchor.delivery_fee_usd, 0.99), 9.99)
            anchor.service_fee_pct = round(min(max(doordash.service_fee_pct + rng.uniform(-1.0, 1.0), 0), 18), 2)
            anchor.eta_min = int(min(max(doordash.eta_min + rng.randint(-3, 3), 15), 70))
            anchor.rating = round(min(max(doordash.rating + rng.uniform(-0.18, 0.18), 2.8), 4.9), 2)
            set_item_prices(anchor, required, multiplier=rng.uniform(0.97, 1.03))
            apply_reliability_fields(doordash, rng, bias=0.10)
            apply_reliability_fields(anchor, rng, bias=0.10)
            return

        if scenario_type == "exact_tie":
            base_fee = round_money(rng.uniform(2.5, 4.0))
            base_service = round(rng.uniform(5.0, 8.5), 2)
            base_eta = rng.randint(24, 34)
            base_rating = round(rng.uniform(4.1, 4.7), 2)

            doordash.delivery_fee_usd = base_fee
            doordash.service_fee_pct = base_service
            doordash.eta_min = base_eta
            doordash.rating = base_rating
            set_item_prices(doordash, required, multiplier=1.0)

            anchor.delivery_fee_usd = round_money(base_fee + rng.uniform(-0.05, 0.05))
            anchor.service_fee_pct = round(min(max(base_service + rng.uniform(-0.3, 0.3), 0), 18), 2)
            anchor.eta_min = base_eta + rng.choice([-1, 0, 0, 0, 1])
            anchor.rating = round(min(max(base_rating + rng.uniform(-0.08, 0.08), 2.8), 4.9), 2)
            set_item_prices(anchor, required, multiplier=rng.uniform(0.995, 1.005))
            apply_reliability_fields(doordash, rng, bias=0.10)
            apply_reliability_fields(anchor, rng, bias=0.10)
            return

        if scenario_type == "dd_advantaged":
            doordash.delivery_fee_usd = round_money(rng.uniform(1.8, 3.2))
            doordash.service_fee_pct = round(rng.uniform(4.0, 7.5), 2)
            doordash.eta_min = rng.randint(22, 30)
            doordash.rating = round(rng.uniform(4.3, 4.9), 2)
            set_item_prices(doordash, required, multiplier=rng.uniform(0.94, 0.99))

            anchor.delivery_fee_usd = round_money(rng.uniform(1.5, 2.8))
            anchor.service_fee_pct = round(rng.uniform(3.5, 7.0), 2)
            anchor.eta_min = rng.randint(20, 28)
            anchor.rating = round(rng.uniform(4.2, 4.9), 2)
            set_item_prices(anchor, required, multiplier=rng.uniform(0.92, 0.98))
            apply_reliability_fields(doordash, rng, bias=0.18)
            apply_reliability_fields(anchor, rng, bias=0.12)
            return

        # competitive (clone market): DoorDash can be strong on one major axis.
        axis = rng.choice(["price", "eta", "reliability"])
        doordash.delivery_fee_usd = round_money(rng.uniform(1.9, 3.8))
        doordash.service_fee_pct = round(rng.uniform(4.0, 8.2), 2)
        doordash.rating = round(rng.uniform(4.1, 4.9), 2)

        if axis == "price":
            doordash.eta_min = rng.randint(24, 34)
            set_item_prices(doordash, required, multiplier=rng.uniform(0.93, 0.99))
            dd_bias = 0.12
        elif axis == "eta":
            doordash.eta_min = rng.randint(18, 24)
            set_item_prices(doordash, required, multiplier=rng.uniform(0.98, 1.03))
            dd_bias = 0.12
        else:
            doordash.eta_min = rng.randint(22, 32)
            set_item_prices(doordash, required, multiplier=rng.uniform(0.98, 1.05))
            dd_bias = 0.30

        anchor.delivery_fee_usd = round_money(rng.uniform(2.1, 4.4))
        anchor.service_fee_pct = round(rng.uniform(4.2, 9.8), 2)
        anchor.eta_min = rng.randint(22, 36)
        anchor.rating = round(rng.uniform(3.9, 4.8), 2)
        apply_reliability_fields(doordash, rng, bias=dd_bias)
        apply_reliability_fields(anchor, rng, bias=0.08)
        return

    if scenario_type == "dominated":
        doordash.delivery_fee_usd = round_money(rng.uniform(4.5, 6.6))
        doordash.service_fee_pct = round(rng.uniform(9.0, 14.0), 2)
        doordash.eta_min = rng.randint(34, 46)
        doordash.rating = round(rng.uniform(3.7, 4.4), 2)
        set_item_prices(doordash, required, multiplier=rng.uniform(1.03, 1.10))

        anchor.delivery_fee_usd = round_money(rng.uniform(1.8, 3.2))
        anchor.service_fee_pct = round(rng.uniform(4.0, 9.0), 2)
        anchor.eta_min = rng.randint(22, 32)
        anchor.rating = round(rng.uniform(4.2, 4.9), 2)
        set_item_prices(anchor, required, multiplier=rng.uniform(0.90, 0.97))
        apply_reliability_fields(doordash, rng, bias=0.0)
        apply_reliability_fields(anchor, rng, bias=0.1)
        return

    if scenario_type == "near_tie":
        doordash.delivery_fee_usd = round_money(rng.uniform(2.4, 4.4))
        doordash.service_fee_pct = round(rng.uniform(5.0, 10.0), 2)
        doordash.eta_min = rng.randint(24, 38)
        doordash.rating = round(rng.uniform(3.9, 4.7), 2)

        anchor.delivery_fee_usd = round_money(doordash.delivery_fee_usd + rng.uniform(-0.4, 0.4))
        anchor.delivery_fee_usd = min(max(anchor.delivery_fee_usd, 0.99), 9.99)
        anchor.service_fee_pct = round(min(max(doordash.service_fee_pct + rng.uniform(-1.5, 1.5), 0), 18), 2)
        anchor.eta_min = int(min(max(doordash.eta_min + rng.randint(-4, 4), 15), 70))
        anchor.rating = round(min(max(doordash.rating + rng.uniform(-0.25, 0.25), 2.8), 4.9), 2)
        set_item_prices(anchor, required, multiplier=rng.uniform(0.96, 1.04))
        apply_reliability_fields(doordash, rng, bias=0.1)
        apply_reliability_fields(anchor, rng, bias=0.1)
        return

    if scenario_type == "exact_tie":
        base_fee = round_money(rng.uniform(2.5, 4.0))
        base_service = round(rng.uniform(5.0, 9.0), 2)
        base_eta = rng.randint(24, 36)
        base_rating = round(rng.uniform(4.0, 4.7), 2)

        doordash.delivery_fee_usd = base_fee
        doordash.service_fee_pct = base_service
        doordash.eta_min = base_eta
        doordash.rating = base_rating
        set_item_prices(doordash, required, multiplier=1.0)

        anchor.delivery_fee_usd = round_money(base_fee + rng.uniform(-0.05, 0.05))
        anchor.service_fee_pct = round(min(max(base_service + rng.uniform(-0.3, 0.3), 0), 18), 2)
        anchor.eta_min = base_eta + rng.choice([-1, 0, 0, 0, 1])
        anchor.rating = round(min(max(base_rating + rng.uniform(-0.1, 0.1), 2.8), 4.9), 2)
        set_item_prices(anchor, required, multiplier=rng.uniform(0.995, 1.005))
        apply_reliability_fields(doordash, rng, bias=0.10)
        apply_reliability_fields(anchor, rng, bias=0.10)
        return

    if scenario_type == "dd_advantaged":
        doordash.delivery_fee_usd = round_money(rng.uniform(1.8, 3.2))
        doordash.service_fee_pct = round(rng.uniform(4.0, 7.5), 2)
        doordash.eta_min = rng.randint(22, 30)
        doordash.rating = round(rng.uniform(4.3, 4.9), 2)
        set_item_prices(doordash, required, multiplier=rng.uniform(0.94, 0.99))

        anchor.delivery_fee_usd = round_money(rng.uniform(1.5, 2.8))
        anchor.service_fee_pct = round(rng.uniform(3.5, 7.0), 2)
        anchor.eta_min = rng.randint(20, 28)
        anchor.rating = round(rng.uniform(4.2, 4.9), 2)
        set_item_prices(anchor, required, multiplier=rng.uniform(0.92, 0.98))
        apply_reliability_fields(doordash, rng, bias=0.18)
        apply_reliability_fields(anchor, rng, bias=0.12)
        return

    # competitive
    axis = "price" if rng.random() < 0.5 else "eta"
    doordash.delivery_fee_usd = round_money(rng.uniform(1.8, 3.6))
    doordash.service_fee_pct = round(rng.uniform(3.0, 8.5), 2)
    doordash.rating = round(rng.uniform(4.0, 4.9), 2)

    if axis == "price":
        doordash.eta_min = rng.randint(26, 38)
        set_item_prices(doordash, required, multiplier=rng.uniform(0.90, 0.97))
        anchor.eta_min = rng.randint(24, 40)
    else:
        doordash.eta_min = rng.randint(18, 24)
        set_item_prices(doordash, required, multiplier=rng.uniform(0.95, 1.03))
        anchor.eta_min = rng.randint(25, 39)

    anchor.delivery_fee_usd = round_money(rng.uniform(2.4, 4.8))
    anchor.service_fee_pct = round(rng.uniform(5.0, 11.0), 2)
    anchor.rating = round(rng.uniform(3.7, 4.8), 2)
    apply_reliability_fields(doordash, rng, bias=0.2)
    apply_reliability_fields(anchor, rng, bias=0.0)


def _reforce_exact_ties(
    rng: random.Random,
    doordash: Vendor,
    targets: List[Vendor],
    request: UserRequest,
) -> None:
    """After compression, snap tie targets back to DoorDash's metrics."""
    dd_order = compute_order_total(doordash, request)
    if dd_order is None:
        return
    required = list(request.required_items)
    for target in targets:
        target_order = compute_order_total(target, request)
        if target_order is None:
            continue
        if target_order["subtotal"] > 0 and dd_order["subtotal"] > 0:
            ratio = dd_order["subtotal"] / target_order["subtotal"]
            jitter = rng.uniform(0.998, 1.002)
            set_item_prices(target, required, multiplier=ratio * jitter)
        target.delivery_fee_usd = round_money(doordash.delivery_fee_usd + rng.uniform(-0.03, 0.03))
        target.service_fee_pct = round(
            min(max(doordash.service_fee_pct + rng.uniform(-0.2, 0.2), 0), 18), 2
        )
        target.eta_min = doordash.eta_min + rng.choice([-1, 0, 0, 0, 1])
        target.rating = round(min(max(doordash.rating + rng.uniform(-0.06, 0.06), 2.8), 4.9), 2)


def _pick_extra_tie_targets(
    scenario_type: str,
    synthetics: List[Vendor],
    cfg: dict,
) -> List[Vendor]:
    """For exact_tie, pick additional synthetics that should be forced to match DoorDash."""
    if scenario_type != "exact_tie":
        return []
    thresholds = cfg.get("relationship_thresholds", {})
    min_clones = int(thresholds.get("exact_tie_min_clones", 3))
    feasible = [v for v in synthetics[1:] if len(v.menu) >= 2]
    return feasible[: max(min_clones, 4)]


def generate_episode(
    rng: random.Random,
    cfg: dict,
    episode_idx: int,
    catalog: Dict[str, CatalogItem],
    popular_ids: List[str],
) -> Episode:
    market_profile = str(cfg.get("market_profile", "v0"))
    dominated_count = int(cfg.get("dominated_episodes", 0))
    near_tie_count = int(cfg.get("near_tie_episodes", 0))
    exact_tie_count = int(cfg.get("exact_tie_episodes", 0))
    dd_advantaged_count = int(cfg.get("dd_advantaged_episodes", 0))

    boundary_near = dominated_count
    boundary_exact = boundary_near + near_tie_count
    boundary_adv = boundary_exact + exact_tie_count
    boundary_dadv = boundary_adv + dd_advantaged_count

    if episode_idx < boundary_near:
        scenario_type = "dominated"
    elif episode_idx < boundary_exact:
        scenario_type = "near_tie"
    elif episode_idx < boundary_adv:
        scenario_type = "exact_tie"
    elif episode_idx < boundary_dadv:
        scenario_type = "dd_advantaged"
    else:
        scenario_type = "competitive"

    request = generate_request(rng, episode_idx, popular_ids)
    menu_cfg = cfg["menus"]
    ranges = cfg["ranges"]

    doordash = generate_doordash_vendor(
        rng=rng,
        episode_idx=episode_idx,
        catalog=catalog,
        popular_ids=popular_ids,
        required_items=request.required_items,
        doordash_item_count=menu_cfg["doordash_items"],
        ranges=ranges,
        market_profile=market_profile,
    )

    dd_price_map = {item.item_id: item.price_usd for item in doordash.menu}

    synthetics: List[Vendor] = []
    for vendor_idx in range(1, cfg["vendors_per_episode"]):
        synthetics.append(
            generate_synthetic_vendor(
                rng=rng,
                episode_idx=episode_idx,
                vendor_idx=vendor_idx,
                catalog=catalog,
                popular_ids=popular_ids,
                required_items=request.required_items,
                doordash_price_map=dd_price_map,
                min_items=menu_cfg["synthetic_items_min"],
                max_items=menu_cfg["synthetic_items_max"],
                cheaper_bias_ratio=menu_cfg["synthetic_cheaper_ratio"],
                ranges=ranges,
                include_all_required=bool(menu_cfg.get("synthetic_include_all_required", True)),
                required_item_prob=float(menu_cfg.get("synthetic_required_item_prob", 1.0)),
            )
        )

    dispersion_cfg = cfg.get("dispersion", {})
    total_ratio_min = float(dispersion_cfg.get("total_ratio_min", dispersion_cfg.get("max_total_ratio", 1.55)))
    total_ratio_max = float(dispersion_cfg.get("total_ratio_max", total_ratio_min))
    eta_range_min = int(dispersion_cfg.get("eta_range_min", dispersion_cfg.get("max_eta_range", 18)))
    eta_range_max = int(dispersion_cfg.get("eta_range_max", eta_range_min))

    target_total_ratio = rng.uniform(min(total_ratio_min, total_ratio_max), max(total_ratio_min, total_ratio_max))
    target_eta_range = rng.randint(min(eta_range_min, eta_range_max), max(eta_range_min, eta_range_max))

    anchor = synthetics[0]
    extra_tie_targets = _pick_extra_tie_targets(scenario_type, synthetics, cfg)

    for _ in range(5):
        force_relationship(rng, scenario_type, doordash, anchor, request, market_profile=market_profile)
        for extra in extra_tie_targets:
            force_relationship(rng, scenario_type, doordash, extra, request, market_profile=market_profile)

        compress_market_dispersion(
            [doordash] + synthetics,
            request,
            max_total_ratio=target_total_ratio,
            max_eta_range=target_eta_range,
        )

        if scenario_type == "exact_tie":
            _reforce_exact_ties(rng, doordash, [anchor] + extra_tie_targets, request)

        episode = Episode(
            episode_id=f"episode_{episode_idx + 1:03d}",
            scenario_type=scenario_type,
            vendors=[doordash] + synthetics,
            request=request,
            seed=cfg["seed"] + episode_idx,
        )
        if relationship_holds_with_thresholds(episode, cfg.get("relationship_thresholds")):
            break

    vendors = [doordash] + synthetics
    rng.shuffle(vendors)

    return Episode(
        episode_id=f"episode_{episode_idx + 1:03d}",
        scenario_type=scenario_type,
        vendors=vendors,
        request=request,
        seed=cfg["seed"] + episode_idx,
    )


def generate_episodes(cfg: dict) -> List[Episode]:
    total = cfg["num_episodes"]
    expected = (
        int(cfg.get("dominated_episodes", 0))
        + int(cfg.get("near_tie_episodes", 0))
        + int(cfg.get("exact_tie_episodes", 0))
        + int(cfg.get("dd_advantaged_episodes", 0))
        + int(cfg.get("competitive_episodes", 0))
    )
    if total != expected:
        raise ValueError(f"num_episodes ({total}) must equal scenario split total ({expected})")

    rng = random.Random(cfg["seed"])
    catalog_items = build_catalog()
    catalog = {item.item_id: item for item in catalog_items}
    popular_ids = [item.item_id for item in catalog_items[:20]]

    episodes: List[Episode] = []
    for idx in range(total):
        episode: Optional[Episode] = None
        for _ in range(25):
            candidate = generate_episode(rng, cfg, idx, catalog, popular_ids)
            if not relationship_holds_with_thresholds(candidate, cfg.get("relationship_thresholds")):
                continue

            feasible_min = int(cfg.get("feasible_vendors_min", 1))
            feasible_max = int(cfg.get("feasible_vendors_max", cfg["vendors_per_episode"]))
            feasible_count = feasible_vendor_count(candidate.vendors, candidate.request)
            if feasible_count < feasible_min or feasible_count > feasible_max:
                continue

            episode = candidate
            break

        if episode is None:
            raise RuntimeError(f"episode_{idx + 1:03d} failed scenario relationship checks after retries")

        if len(episode.vendors) != cfg["vendors_per_episode"]:
            raise RuntimeError(f"{episode.episode_id} did not generate {cfg['vendors_per_episode']} vendors")
        doordash_count = sum(1 for vendor in episode.vendors if vendor.is_doordash)
        if doordash_count != 1:
            raise RuntimeError(f"{episode.episode_id} should include exactly one DoorDash vendor")
        episodes.append(episode)

    return episodes


def write_episodes(path: str, episodes: List[Episode]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for episode in episodes:
            f.write(json.dumps(episode.model_dump(), ensure_ascii=True) + "\n")


def generate_seed_sweep(cfg: dict, seeds: List[int]) -> Dict[int, List[Episode]]:
    """Generate episodes for multiple seeds, returning {seed: episodes}."""
    result: Dict[int, List[Episode]] = {}
    for seed in seeds:
        sweep_cfg = dict(cfg)
        sweep_cfg["seed"] = seed
        result[seed] = generate_episodes(sweep_cfg)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate DoorDash vs AI synthetic world episodes")
    parser.add_argument("--config", required=True, help="Path to YAML config")
    parser.add_argument("--out", required=True, help="Output JSONL path")
    parser.add_argument(
        "--seeds",
        type=str,
        default=None,
        help="Comma-separated seeds for sweep (e.g. '100,200,300'). "
        "Outputs to <out_stem>_seed_<N>.jsonl per seed.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)

    if args.seeds:
        seeds = [int(s.strip()) for s in args.seeds.split(",")]
        sweep = generate_seed_sweep(cfg, seeds)
        out_path = Path(args.out)
        stem = out_path.stem
        for seed, episodes in sweep.items():
            seed_path = str(out_path.parent / f"{stem}_seed_{seed}.jsonl")
            write_episodes(seed_path, episodes)
            print(f"Seed {seed}: {len(episodes)} episodes -> {seed_path}")
    else:
        episodes = generate_episodes(cfg)
        write_episodes(args.out, episodes)
        print(f"Generated {len(episodes)} episodes -> {args.out}")


if __name__ == "__main__":
    main()

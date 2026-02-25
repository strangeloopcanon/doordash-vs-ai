from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import random
import time
from pathlib import Path
from typing import List, Optional, Tuple

import yaml
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI, RateLimitError

from generate_world import compute_order_total
from models import AgentChoice, Episode, RunRecord, Vendor


SYSTEM_PROMPT = (
    "You are a personal food-delivery assistant. Choose exactly one vendor and a cart that "
    "satisfies the user request. Use only vendor_id and item_id values present in the input data. "
    "Reliability is represented by rating, cancel_rate_pct, on_time_rate_pct, and reliability_score."
)

CHOICE_SCHEMA = {
    "type": "json_schema",
    "name": "vendor_choice",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "chosen_vendor_id": {"type": "string"},
            "chosen_items": {"type": "array", "items": {"type": "string"}},
            "reasoning": {"type": "string"},
            "factors": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["chosen_vendor_id", "chosen_items", "reasoning", "factors"],
    },
}


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


def build_prompt(episode: Episode) -> str:
    vendors_payload = []
    for vendor in episode.vendors:
        vendors_payload.append(
            {
                "vendor_id": vendor.vendor_id,
                "name": vendor.name,
                "is_doordash": vendor.is_doordash,
                "delivery_fee_usd": vendor.delivery_fee_usd,
                "service_fee_pct": vendor.service_fee_pct,
                "eta_min": vendor.eta_min,
                "rating": vendor.rating,
                "cancel_rate_pct": vendor.cancel_rate_pct,
                "on_time_rate_pct": vendor.on_time_rate_pct,
                "reliability_score": vendor.reliability_score,
                "menu": [
                    {"item_id": item.item_id, "name": item.name, "price_usd": item.price_usd}
                    for item in vendor.menu
                ],
            }
        )

    request_payload = {
        "request_id": episode.request.request_id,
        "text": episode.request.text,
        "required_items": episode.request.required_items,
        "quantity_map": episode.request.quantity_map,
        "priority_hint": episode.request.priority_hint,
    }

    prompt = {
        "task": "Choose the best single vendor and cart for this user request.",
        "constraints": [
            "chosen_vendor_id must be one of the vendor_id values below",
            "chosen_items must be item_id values from the chosen vendor menu",
            "chosen_items must include all required_items",
            "keep reasoning concise",
        ],
        "request": request_payload,
        "vendors": vendors_payload,
    }
    return json.dumps(prompt, ensure_ascii=True)


def find_vendor(episode: Episode, vendor_id: str) -> Optional[Vendor]:
    for vendor in episode.vendors:
        if vendor.vendor_id == vendor_id:
            return vendor
    return None


def evaluate_choice_feasibility(choice: AgentChoice, episode: Episode) -> Tuple[bool, float, str, Optional[Vendor]]:
    vendor = find_vendor(episode, choice.chosen_vendor_id)
    if vendor is None:
        return False, 0.0, "chosen_vendor_id not found", None

    chosen_items = set(choice.chosen_items)
    required_items = set(episode.request.required_items)
    if not required_items.issubset(chosen_items):
        return False, 0.0, "chosen_items missing required items", vendor

    menu_map = {item.item_id: item for item in vendor.menu}
    for item_id in chosen_items:
        if item_id not in menu_map:
            return False, 0.0, "chosen_items contain item not in vendor menu", vendor

    subtotal = 0.0
    for item_id in chosen_items:
        qty = episode.request.quantity_map.get(item_id, 1)
        subtotal += menu_map[item_id].price_usd * qty

    return True, round(subtotal, 2), "", vendor


def parse_agent_output(raw_output: str) -> Tuple[bool, Optional[AgentChoice], str]:
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        return False, None, f"invalid_json: {exc.msg}"

    try:
        return True, AgentChoice.model_validate(payload), ""
    except Exception as exc:  # pydantic errors
        return False, None, f"invalid_schema: {exc}"


def mock_choice_for_episode(episode: Episode) -> AgentChoice:
    feasible = []
    for vendor in episode.vendors:
        order = compute_order_total(vendor, episode.request)
        if order is not None:
            feasible.append((vendor, order))

    if not feasible:
        return AgentChoice(
            chosen_vendor_id=episode.vendors[0].vendor_id,
            chosen_items=list(episode.request.required_items),
            reasoning="No feasible vendors found; default fallback.",
            factors=["fallback"],
        )

    priority = episode.request.priority_hint
    if priority == "value":
        winner = min(feasible, key=lambda x: (x[1]["total"], x[1]["eta_min"], -x[1]["rating"]))
        factors = ["lowest_total", "tie_break_eta"]
    elif priority == "fast":
        winner = min(feasible, key=lambda x: (x[1]["eta_min"], x[1]["total"], -x[1]["rating"]))
        factors = ["fastest_eta", "tie_break_total"]
    elif priority == "rating":
        winner = max(
            feasible,
            key=lambda x: (
                x[0].reliability_score,
                x[1]["rating"],
                -x[1]["total"],
                -x[1]["eta_min"],
            ),
        )
        factors = ["highest_reliability", "tie_break_total"]
    else:
        winner = min(
            feasible,
            key=lambda x: (
                0.45 * x[1]["total"]
                + 0.30 * x[1]["eta_min"]
                - 8.0 * (x[0].reliability_score / 100.0)
                - 1.5 * x[1]["rating"]
            ),
        )
        factors = ["balanced_total_eta_reliability"]

    vendor = winner[0]
    return AgentChoice(
        chosen_vendor_id=vendor.vendor_id,
        chosen_items=list(episode.request.required_items),
        reasoning="Mock runner selected vendor by deterministic policy.",
        factors=factors,
    )


async def fetch_response_with_retry(
    client: AsyncOpenAI,
    model: str,
    prompt: str,
    max_output_tokens: int,
    max_retries: int,
    retry_backoff_seconds: float,
) -> object:
    attempt = 0
    while True:
        try:
            return await client.responses.create(
                model=model,
                instructions=SYSTEM_PROMPT,
                input=prompt,
                max_output_tokens=max_output_tokens,
                text={"format": CHOICE_SCHEMA},
            )
        except RateLimitError as exc:
            if attempt >= max_retries:
                raise RuntimeError(f"rate_limit_after_retries: {exc}") from exc
        except APIStatusError as exc:
            if exc.status_code < 500 or attempt >= max_retries:
                raise
        except (APIConnectionError, APITimeoutError) as exc:
            if attempt >= max_retries:
                raise RuntimeError(f"network_timeout_after_retries: {exc}") from exc

        attempt += 1
        backoff = retry_backoff_seconds * (2 ** (attempt - 1))
        await asyncio.sleep(backoff)


async def run_single_episode(
    semaphore: asyncio.Semaphore,
    episode: Episode,
    client: Optional[AsyncOpenAI],
    model: str,
    max_output_tokens: int,
    max_retries: int,
    retry_backoff_seconds: float,
    use_mock: bool,
) -> RunRecord:
    async with semaphore:
        started = time.perf_counter()
        raw_output = ""
        tokens_in = 0
        tokens_out = 0
        error: Optional[str] = None

        try:
            if use_mock:
                choice = mock_choice_for_episode(episode)
                parse_ok = True
            else:
                if client is None:
                    raise RuntimeError("OpenAI client not configured")

                prompt = build_prompt(episode)
                response = await fetch_response_with_retry(
                    client=client,
                    model=model,
                    prompt=prompt,
                    max_output_tokens=max_output_tokens,
                    max_retries=max_retries,
                    retry_backoff_seconds=retry_backoff_seconds,
                )
                raw_output = response.output_text or ""
                parse_ok, choice, parse_error = parse_agent_output(raw_output)
                if not parse_ok:
                    error = parse_error
                usage = getattr(response, "usage", None)
                if usage is not None:
                    tokens_in = int(getattr(usage, "input_tokens", 0) or 0)
                    tokens_out = int(getattr(usage, "output_tokens", 0) or 0)

            if not parse_ok or choice is None:
                latency_ms = int((time.perf_counter() - started) * 1000)
                return RunRecord(
                    episode_id=episode.episode_id,
                    scenario_type=episode.scenario_type,
                    priority_hint=episode.request.priority_hint,
                    chosen_vendor_id="",
                    chosen_vendor_name="",
                    is_doordash_choice=False,
                    parse_ok=False,
                    feasible_choice=False,
                    est_subtotal_usd=0.0,
                    rationale="",
                    factors_json="[]",
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    latency_ms=latency_ms,
                    error=error,
                    raw_output=raw_output,
                )

            feasible, subtotal, feasibility_error, vendor = evaluate_choice_feasibility(choice, episode)
            latency_ms = int((time.perf_counter() - started) * 1000)
            return RunRecord(
                episode_id=episode.episode_id,
                scenario_type=episode.scenario_type,
                priority_hint=episode.request.priority_hint,
                chosen_vendor_id=choice.chosen_vendor_id,
                chosen_vendor_name=vendor.name if vendor else "",
                is_doordash_choice=bool(vendor.is_doordash) if vendor else False,
                parse_ok=True,
                feasible_choice=feasible,
                est_subtotal_usd=subtotal,
                rationale=choice.reasoning,
                factors_json=json.dumps(choice.factors, ensure_ascii=True),
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                error=feasibility_error if not feasible else None,
                raw_output=raw_output if raw_output else None,
            )

        except Exception as exc:  # defensive catch, keep batch running
            latency_ms = int((time.perf_counter() - started) * 1000)
            return RunRecord(
                episode_id=episode.episode_id,
                scenario_type=episode.scenario_type,
                priority_hint=episode.request.priority_hint,
                chosen_vendor_id="",
                chosen_vendor_name="",
                is_doordash_choice=False,
                parse_ok=False,
                feasible_choice=False,
                est_subtotal_usd=0.0,
                rationale="",
                factors_json="[]",
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                error=str(exc),
                raw_output=raw_output if raw_output else None,
            )


async def run_experiment(
    cfg: dict,
    episodes: List[Episode],
    use_mock: bool,
    batch_size: Optional[int] = None,
) -> List[RunRecord]:
    concurrency = batch_size or int(cfg.get("batch_size", 4))
    semaphore = asyncio.Semaphore(concurrency)

    model = cfg.get("model", "gpt-5.2")
    max_retries = int(cfg.get("max_retries", 3))
    retry_backoff_seconds = float(cfg.get("retry_backoff_seconds", 1.5))
    max_output_tokens = int(cfg.get("max_output_tokens", 700))

    api_key = os.getenv("OPENAI_API_KEY")
    client: Optional[AsyncOpenAI] = None
    if not use_mock:
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is missing. Set it or run with --mock.")
        client = AsyncOpenAI(api_key=api_key)

    tasks = [
        asyncio.create_task(
            run_single_episode(
                semaphore=semaphore,
                episode=episode,
                client=client,
                model=model,
                max_output_tokens=max_output_tokens,
                max_retries=max_retries,
                retry_backoff_seconds=retry_backoff_seconds,
                use_mock=use_mock,
            )
        )
        for episode in episodes
    ]
    results = await asyncio.gather(*tasks)

    if client is not None:
        await client.close()

    return sorted(results, key=lambda r: r.episode_id)


def write_runs_csv(path: str, records: List[RunRecord]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(RunRecord.model_fields.keys())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record.model_dump())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DoorDash-vs-synthetic selection using OpenAI Responses API")
    parser.add_argument("--config", required=True, help="Path to YAML config")
    parser.add_argument("--episodes", required=True, help="Input episodes JSONL")
    parser.add_argument("--out", required=True, help="Output runs CSV")
    parser.add_argument("--mock", action="store_true", help="Use deterministic mock policy instead of API calls")
    parser.add_argument("--batch-size", type=int, default=None, help="Override batch size")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    episodes = load_episodes(args.episodes)

    records = asyncio.run(
        run_experiment(
            cfg=cfg,
            episodes=episodes,
            use_mock=args.mock,
            batch_size=args.batch_size,
        )
    )
    write_runs_csv(args.out, records)

    parse_failures = sum(1 for r in records if not r.parse_ok)
    infeasible = sum(1 for r in records if r.parse_ok and not r.feasible_choice)
    print(f"Completed {len(records)} episodes -> {args.out}")
    print(f"parse_failures={parse_failures}, infeasible={infeasible}")


if __name__ == "__main__":
    main()

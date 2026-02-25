from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List

from models import AgentChoice, Episode, RunRecord
from run_responses import evaluate_choice_feasibility, parse_agent_output


def load_episodes(path: str) -> List[Episode]:
    episodes: List[Episode] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                episodes.append(Episode.model_validate_json(line))
    return episodes


def write_runs_csv(path: str, rows: List[RunRecord]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "episode_id",
        "scenario_type",
        "priority_hint",
        "chosen_vendor_id",
        "chosen_vendor_name",
        "is_doordash_choice",
        "parse_ok",
        "feasible_choice",
        "est_subtotal_usd",
        "rationale",
        "factors_json",
        "tokens_in",
        "tokens_out",
        "latency_ms",
        "error",
        "raw_output",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.model_dump())


def compile_records(episodes: List[Episode], choices_dir: str) -> List[RunRecord]:
    by_episode: Dict[str, Episode] = {ep.episode_id: ep for ep in episodes}
    records: List[RunRecord] = []

    for episode_id, episode in sorted(by_episode.items()):
        choice_path = Path(choices_dir) / f"{episode_id}.json"
        if not choice_path.exists():
            records.append(
                RunRecord(
                    episode_id=episode_id,
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
                    tokens_in=0,
                    tokens_out=0,
                    latency_ms=0,
                    error="missing_choice_file",
                    raw_output=None,
                )
            )
            continue

        raw_output = choice_path.read_text(encoding="utf-8").strip()
        parse_ok, choice, parse_error = parse_agent_output(raw_output)
        if not parse_ok:
            parse_ok, choice, parse_error = parse_with_normalization(raw_output)
        if not parse_ok or choice is None:
            records.append(
                RunRecord(
                    episode_id=episode_id,
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
                    tokens_in=0,
                    tokens_out=0,
                    latency_ms=0,
                    error=parse_error,
                    raw_output=raw_output,
                )
            )
            continue

        feasible, subtotal, feasibility_error, vendor = evaluate_choice_feasibility(choice, episode)
        records.append(
            RunRecord(
                episode_id=episode_id,
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
                tokens_in=0,
                tokens_out=0,
                latency_ms=0,
                error=feasibility_error if not feasible else None,
                raw_output=raw_output,
            )
        )

    return records


def parse_with_normalization(raw_output: str) -> tuple[bool, AgentChoice | None, str]:
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        return False, None, f"invalid_json: {exc.msg}"

    if not isinstance(payload, dict):
        return False, None, "invalid_schema: payload is not an object"

    chosen_vendor_id = str(payload.get("chosen_vendor_id", "")).strip()
    reasoning = str(payload.get("reasoning", "")).strip()

    chosen_items_raw = payload.get("chosen_items", [])
    chosen_items: List[str] = []
    if isinstance(chosen_items_raw, list):
        for item in chosen_items_raw:
            if isinstance(item, str):
                val = item.strip()
                if val:
                    chosen_items.append(val)
            elif isinstance(item, dict):
                # Common variant from subagents: {"item": "...", ...}
                item_id = item.get("item_id") or item.get("item")
                if item_id:
                    chosen_items.append(str(item_id).strip())

    factors_raw = payload.get("factors", [])
    factors: List[str] = []
    if isinstance(factors_raw, list):
        factors = [str(x).strip() for x in factors_raw if str(x).strip()]
    elif isinstance(factors_raw, dict):
        for key, value in factors_raw.items():
            key_s = str(key).strip()
            if not key_s:
                continue
            if isinstance(value, (dict, list)):
                value_s = json.dumps(value, ensure_ascii=True)
            else:
                value_s = str(value).strip()
            factors.append(f"{key_s}: {value_s}" if value_s else key_s)

    normalized = {
        "chosen_vendor_id": chosen_vendor_id,
        "chosen_items": chosen_items,
        "reasoning": reasoning,
        "factors": factors,
    }

    try:
        return True, AgentChoice.model_validate(normalized), ""
    except Exception as exc:
        return False, None, f"invalid_schema_after_normalization: {exc}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compile subagent JSON choices into llm_runs CSV format")
    parser.add_argument("--episodes", required=True, help="Path to episodes JSONL")
    parser.add_argument("--choices-dir", required=True, help="Directory containing episode_XXX.json choice files")
    parser.add_argument("--out", required=True, help="Output llm runs CSV")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    episodes = load_episodes(args.episodes)
    records = compile_records(episodes, args.choices_dir)
    write_runs_csv(args.out, records)
    print(f"Wrote {len(records)} run records -> {args.out}")


if __name__ == "__main__":
    main()

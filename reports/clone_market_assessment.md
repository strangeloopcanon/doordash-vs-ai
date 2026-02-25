# Clone-Market Assessment (New Run Only)

Generated: 2026-02-24 UTC

## Summary

This run uses a clone-style market distribution (tight spreads, partial menu overlap, and less coupling between rating and reliability).

- LLM (subagent chooser) DoorDash surfacing: **0/20 = 0.0%** (95% CI: **[0.0%, 16.1%]**).
- Deterministic baselines mostly surface DoorDash at **5.0%**, except ETA-first at **20.0%**.
- Random-equation surfacing: **87/2000 = 4.3%** (95% CI: **[3.5%, 5.3%]**).

## Setup (Clone Profile)

| Item | Value |
| --- | --- |
| Config | `configs/v1_clone.yaml` |
| Episodes | 20 |
| Vendors per episode | 100 (1 DoorDash + 99 synthetic) |
| Scenario split | dominated=3, near_tie=11, competitive=6 |
| LLM result file | `results/llm_runs_subagents_clone_20.csv` |
| Baseline file | `results/baselines_clone_20.csv` |

## Market Realism Diagnostics

| Metric | Observed |
| --- | --- |
| Feasible vendors per episode | mean **74.2**, min **62**, max **80** |
| Required-total max/min ratio | mean **1.209**, min **1.156**, max **1.244** |
| ETA range per episode | mean **14.8 min**, min **8**, max **20** |
| Corr(rating, reliability_score) | **0.384** |

Interpretation: this is much closer to a high-competition clone market than the prior setup.

## Selection Results

| Policy / Selector | DoorDash surfacing |
| --- | --- |
| LLM chooser (subagent) | **0.0%** (0/20) |
| `price_first` | 5.0% (1/20) |
| `eta_first` | 20.0% (4/20) |
| `rating_first` | 5.0% (1/20) |
| `reliability_first` | 5.0% (1/20) |
| `balanced_equation` | 5.0% (1/20) |
| `random_equation` | 4.3% (87/2000) |

## Why DoorDash Stayed Low In This Clone World

DoorDash was often competitive, but rarely the top option:

- Total-cost rank (among feasible vendors): mean **49.15**.
- ETA rank: mean **29.55**.
- Rating rank: mean **23.05**.
- Reliability rank: mean **30.55**.
- Best-in-episode counts: total **1**, ETA **4**, rating **1**, reliability **1** (out of 20).

So low LLM surfacing is directionally consistent with the market state we generated.

## Output Artifacts

- Episodes: `data/episodes_clone_20.jsonl`
- Subagent payloads: `data/subagent_payloads_clone_20`
- Subagent choices: `results/subagent_choices_clone_20`
- LLM runs CSV: `results/llm_runs_subagents_clone_20.csv`
- Baselines CSV: `results/baselines_clone_20.csv`
- Main report: `reports/clone_market_report_subagents_20.md`

# Reliability Assessment (New Realistic Run Only)

Generated: 2026-02-24 UTC

## Bottom line

These are good **v0 directional** results, not final decision-grade evidence.

- The pipeline is reliable: parse failure and infeasible-choice rates were both 0%.
- The behavior signal is consistent across repeats: DoorDash surfaced 1/20 in run 1 and 1/20 in run 2.
- Statistical uncertainty is still wide because the sample is small (40 LLM decisions total across 2 repeats).

## Experiment setup (what this document covers)

| Item | Value |
| --- | --- |
| Dataset | `data/episodes_realistic_20.jsonl` |
| Episodes | 20 |
| Vendors per episode | 100 (1 DoorDash + 99 synthetic) |
| Scenario mix | 10 dominated, 5 near-tie, 5 competitive |
| Priority mix | value=5, fast=4, rating=6, balanced=5 |
| LLM runs included | `results/llm_runs_subagents_realistic_20.csv`, `results/llm_runs_subagents_realistic_20_r2.csv` |
| Baselines included | `results/baselines_realistic_20.csv` |
| Reliability fields present | `reliability_score`, `on_time_rate_pct`, `cancel_rate_pct` |

## Core results

| Metric | Run 1 (n=20) | Run 2 (n=20) | Pooled (n=40) |
| --- | --- | --- | --- |
| DoorDash surfacing rate | 5.0% (1/20) | 5.0% (1/20) | 5.0% (2/40) |
| 95% Wilson CI (DoorDash) | [0.9%, 23.6%] | [0.9%, 23.6%] | [1.4%, 16.5%] |
| Parse failure rate | 0.0% | 0.0% | 0.0% |
| Infeasible-choice rate | 0.0% | 0.0% | 0.0% |
| Picked reliability-optimal vendor | 30.0% (6/20) | 35.0% (7/20) | 32.5% (13/40) |

## Deterministic/random baseline comparison (same episodes)

| Policy | DoorDash surfacing |
| --- | --- |
| `price_first` | 5.0% (1/20) |
| `eta_first` | 0.0% (0/20) |
| `rating_first` | 0.0% (0/20) |
| `reliability_first` | 5.0% (1/20) |
| `balanced_equation` | 5.0% (1/20) |
| `random_equation` | 4.3% (86/2000) |

Interpretation: in this world, LLM DoorDash surfacing is basically in line with equation baselines.

## Repeatability and stability checks

| Check | Result |
| --- | --- |
| Run-to-run exact vendor agreement | 85.0% (17/20 episodes) |
| Disagreement episodes | `episode_013`, `episode_014`, `episode_018` |
| DoorDash by scenario type (pooled) | dominated: 0/20, near-tie: 0/10, competitive: 2/10 |

Interpretation: choice behavior is fairly stable run-to-run for a stochastic model, with a small set of flip episodes.

## Why DoorDash stays low here (important context)

DoorDash is often structurally disadvantaged in this synthetic market:

- DoorDash total-cost rank among 100 vendors: mean rank 69.1, median rank 91.0.
- DoorDash ETA rank: mean 53.4, median 62.5.
- DoorDash rating/reliability rank: mean 36.4.
- DoorDash was best on total in 1/20 episodes and best on reliability in 1/20.

This means low surfacing is not surprising for either equations or LLMs under current generation settings.

## Are these "good" results?

Yes for a first experiment.

- Good for instrumentation: generation, feasibility checks, baselines, and LLM runs are all working.
- Good for directional signal: DoorDash does not appear to receive a hidden brand boost in this setup.
- Not yet good for strong causal claims: sample size and synthetic assumptions limit certainty.

## Reliability limits and threats to validity

1. Small LLM sample size.
2. Synthetic-world assumptions drive outcomes heavily.
3. Reliability and rating are highly correlated in generated data (corr ~= 0.94), so their effects are hard to separate.
4. Only one world seed and one model family setup were tested in this report.
5. Subagent chooser is useful operationally but not identical to running all episodes through external Responses API calls.

## What would make this decision-grade

1. Increase episodes to at least 200 (target ~+/-3 percentage points around a 5% rate) and rerun 3-5 repeats.
2. Sweep multiple world seeds (for example 10 seeds) and report variance across seeds.
3. Explicitly test counterfactual worlds where DoorDash is top-5 on reliability but not price, and vice versa.
4. Reduce rating/reliability collinearity in generation so each factor can be identified.
5. Run the same 20-episode set with true Responses API calls for direct comparability.


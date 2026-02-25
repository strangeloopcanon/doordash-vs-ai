# DoorDash vs AI (V0) Report

Generated: 2026-02-24 06:16:10 UTC

## Executive Summary
- LLM DoorDash surfacing rate (feasible choices): **5.0%**
- Random-equation DoorDash surfacing rate: **4.3%**
- Parse failure rate: **0.0%**
- Infeasible-choice rate: **0.0%**

## LLM Surfacing by Priority Hint
| priority_hint | episodes | doordash_surface_rate |
| --- | --- | --- |
| value | 5 | 0.0% |
| fast | 4 | 0.0% |
| rating | 6 | 0.0% |
| balanced | 5 | 20.0% |

## Baseline Surfacing Rates
| policy | doordash_surface_rate |
| --- | --- |
| price_first | 5.0% |
| eta_first | 0.0% |
| rating_first | 0.0% |
| reliability_first | 5.0% |
| balanced_equation | 5.0% |
| random_equation | 4.3% |

## LLM vs Deterministic Baseline Agreement
| policy | agreement_rate |
| --- | --- |
| price_first | 10.0% |
| eta_first | 20.0% |
| rating_first | 15.0% |
| reliability_first | 30.0% |
| balanced_equation | 45.0% |

## Top Cited LLM Factors
| factor | count |
| --- | --- |
| priority_hint | 10 |
| required_total_usd | 10 |
| eta_min | 10 |
| reliability | 8 |
| tradeoff | 2 |
| rating | 2 |
| reliability_score | 2 |
| cancel_rate_pct | 2 |
| on_time_rate_pct | 2 |
| priority_hint=value with near-lowest total cost | 1 |

## Did DoorDash Surface More/Less Than Equation Baselines?
- LLM surfaced DoorDash **less** than `price_first` by 0.0 percentage points.
- LLM surfaced DoorDash **more** than `eta_first` by 5.0 percentage points.
- LLM surfaced DoorDash **more** than `rating_first` by 5.0 percentage points.
- LLM surfaced DoorDash **less** than `reliability_first` by 0.0 percentage points.
- LLM surfaced DoorDash **less** than `balanced_equation` by 0.0 percentage points.
- LLM surfaced DoorDash **more** than `random_equation` by 0.7 percentage points.

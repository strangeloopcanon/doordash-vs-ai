# DoorDash vs AI Clone-Market Report

Generated: 2026-02-24 19:57:37 UTC

## Executive Summary
- LLM DoorDash surfacing rate (feasible choices): **0.0%**
- Random-equation DoorDash surfacing rate: **4.3%**
- Parse failure rate: **0.0%**
- Infeasible-choice rate: **0.0%**

## LLM Surfacing by Priority Hint
| priority_hint | episodes | doordash_surface_rate |
| --- | --- | --- |
| value | 3 | 0.0% |
| fast | 6 | 0.0% |
| rating | 5 | 0.0% |
| balanced | 6 | 0.0% |

## Baseline Surfacing Rates
| policy | doordash_surface_rate |
| --- | --- |
| price_first | 5.0% |
| eta_first | 20.0% |
| rating_first | 5.0% |
| reliability_first | 5.0% |
| balanced_equation | 5.0% |
| random_equation | 4.3% |

## LLM vs Deterministic Baseline Agreement
| policy | agreement_rate |
| --- | --- |
| price_first | 15.0% |
| eta_first | 25.0% |
| rating_first | 5.0% |
| reliability_first | 25.0% |
| balanced_equation | 55.0% |

## Top Cited LLM Factors
| factor | count |
| --- | --- |
| priority_hint: balanced | 6 |
| priority_hint: fast | 5 |
| priority_hint: rating | 4 |
| priority_hint: value | 3 |
| cost_speed_quality_tradeoff: near-cheapest and near-fastest option while keeping quality metrics strong overall. | 1 |
| selected_vendor_metrics: {"required_total_usd": 53.98, "eta_min": 29, "reliability_score": 81.39, "cancel_rate_pct": 8.67, "on_time_rate_pct": 90.05, "rating": 4.85} | 1 |
| comparison_notes: {"vs_cheapest_option": "cheapest total is 51.70 (ep001_vendor_084) but with slower eta (35) and weaker quality/reliability.", "vs_highest_reliability_option": "highest reliability_score is 87.58 (ep001_vendor_092) but with higher total (59.14) and slower eta (35)."} | 1 |
| eta_min: 24 | 1 |
| required_total_usd: 47.13 | 1 |
| reliability_score: 86.8 | 1 |

## Did DoorDash Surface More/Less Than Equation Baselines?
- LLM surfaced DoorDash **less** than `price_first` by 5.0 percentage points.
- LLM surfaced DoorDash **less** than `eta_first` by 20.0 percentage points.
- LLM surfaced DoorDash **less** than `rating_first` by 5.0 percentage points.
- LLM surfaced DoorDash **less** than `reliability_first` by 5.0 percentage points.
- LLM surfaced DoorDash **less** than `balanced_equation` by 5.0 percentage points.
- LLM surfaced DoorDash **less** than `random_equation` by 4.3 percentage points.

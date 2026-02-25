# DoorDash Brand Moat: Advantaged Run

Generated: 2026-02-25 05:38:33 UTC

## Executive Summary
- LLM DoorDash surfacing rate (feasible choices): **0.0%** (95% CI: [0.0%, 16.1%])
- Random-equation DoorDash surfacing rate: **2.6%**
- Parse failure rate: **0.0%**
- Infeasible-choice rate: **0.0%**
- n = 20 feasible LLM decisions

## LLM Surfacing by Priority Hint
| priority_hint | episodes | doordash_surface_rate |
| --- | --- | --- |
| value | 3 | 0.0% |
| fast | 8 | 0.0% |
| rating | 5 | 0.0% |
| balanced | 4 | 0.0% |

## Baseline Surfacing Rates
| policy | doordash_surface_rate |
| --- | --- |
| price_first | 0.0% |
| eta_first | 5.0% |
| rating_first | 0.0% |
| reliability_first | 0.0% |
| balanced_equation | 5.0% |
| random_equation | 2.6% |

## LLM vs Deterministic Baseline Agreement
| policy | agreement_rate |
| --- | --- |
| price_first | 35.0% |
| eta_first | 40.0% |
| rating_first | 10.0% |
| reliability_first | 20.0% |
| balanced_equation | 35.0% |

## Top Cited LLM Factors
| factor | count |
| --- | --- |
| reliability_score | 20 |
| eta_min | 14 |
| required_total_usd | 10 |
| on_time_rate_pct | 9 |
| rating | 7 |
| cancel_rate_pct | 7 |
| total_cost | 4 |

## Did DoorDash Surface More/Less Than Equation Baselines?
- LLM surfaced DoorDash **less** than `price_first` by 0.0pp (p=1.000)
- LLM surfaced DoorDash **less** than `eta_first` by 5.0pp (p=1.000)
- LLM surfaced DoorDash **less** than `rating_first` by 0.0pp (p=1.000)
- LLM surfaced DoorDash **less** than `reliability_first` by 0.0pp (p=1.000)
- LLM surfaced DoorDash **less** than `balanced_equation` by 5.0pp (p=1.000)
- LLM surfaced DoorDash **less** than `random_equation` by 2.6pp (p=1.000)

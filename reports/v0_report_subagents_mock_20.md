# DoorDash vs AI (V0) Report

Generated: 2026-02-24 05:03:00 UTC

## Executive Summary
- LLM DoorDash surfacing rate (feasible choices): **0.0%**
- Random-equation DoorDash surfacing rate: **2.8%**
- Parse failure rate: **0.0%**
- Infeasible-choice rate: **0.0%**

## LLM Surfacing by Priority Hint
| priority_hint | episodes | doordash_surface_rate |
| --- | --- | --- |
| value | 5 | 0.0% |
| fast | 7 | 0.0% |
| rating | 3 | 0.0% |
| balanced | 5 | 0.0% |

## Baseline Surfacing Rates
| policy | doordash_surface_rate |
| --- | --- |
| price_first | 10.0% |
| eta_first | 0.0% |
| rating_first | 0.0% |
| balanced_equation | 5.0% |
| random_equation | 2.8% |

## LLM vs Deterministic Baseline Agreement
| policy | agreement_rate |
| --- | --- |
| price_first | 30.0% |
| eta_first | 40.0% |
| rating_first | 25.0% |
| balanced_equation | 30.0% |

## Top Cited LLM Factors
| factor | count |
| --- | --- |
| tie_break_total | 10 |
| fastest_eta | 7 |
| lowest_total | 5 |
| tie_break_eta | 5 |
| balanced_total_eta_rating | 5 |
| highest_rating | 3 |

## Did DoorDash Surface More/Less Than Equation Baselines?
- LLM surfaced DoorDash **less** than `price_first` by 10.0 percentage points.
- LLM surfaced DoorDash **less** than `eta_first` by 0.0 percentage points.
- LLM surfaced DoorDash **less** than `rating_first` by 0.0 percentage points.
- LLM surfaced DoorDash **less** than `balanced_equation` by 5.0 percentage points.
- LLM surfaced DoorDash **less** than `random_equation` by 2.8 percentage points.

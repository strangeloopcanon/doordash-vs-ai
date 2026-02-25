# Brand Moat Analysis

Generated: 2026-02-25 05:38:34 UTC

## Summary

| Metric | Value |
| --- | --- |
| Episodes analyzed | 20 |
| LLM chose DoorDash | 0/20 (0.0%) |
| DoorDash mean utility rank | 24.1 |
| DoorDash median utility rank | 19 |
| LLM mean regret | 0.1453 |

## Brand Moat Curve

How often does the LLM choose DoorDash at each utility-rank bucket, compared to the balanced equation baseline?

| DoorDash Rank Bucket | Episodes | LLM DoorDash Rate | Equation DoorDash Rate | Gap |
| --- | --- | --- | --- | --- |
| top-1 | 1 | 0.0% | 100.0% | -100.0pp |
| top-5 | 6 | 0.0% | 0.0% | +0.0pp |
| top-10 | 1 | 0.0% | 0.0% | +0.0pp |
| top-25% | 3 | 0.0% | 0.0% | +0.0pp |
| top-50% | 4 | 0.0% | 0.0% | +0.0pp |
| bottom-50% | 5 | 0.0% | 0.0% | +0.0pp |

## Per-Episode Decision Audit

```
episode_001 (dominated, fast) | dd_rank=52/80 | llm_chose=ep001_vendor_054(rank=12) | rational=no | dd_gap=0.372
episode_002 (dominated, rating) | dd_rank=77/79 | llm_chose=ep002_vendor_047(rank=3) | rational=yes | dd_gap=0.527
episode_003 (near_tie, value) | dd_rank=8/80 | llm_chose=ep003_vendor_087(rank=1) | rational=yes | dd_gap=0.211
episode_004 (near_tie, balanced) | dd_rank=31/63 | llm_chose=ep004_vendor_077(rank=1) | rational=yes | dd_gap=0.259
episode_005 (exact_tie, balanced) | dd_rank=11/73 | llm_chose=ep005_vendor_069(rank=18) | rational=no | dd_gap=0.132
episode_006 (exact_tie, balanced) | dd_rank=16/74 | llm_chose=ep006_vendor_086(rank=8) | rational=no | dd_gap=0.200
episode_007 (exact_tie, rating) | dd_rank=60/80 | llm_chose=ep007_vendor_093(rank=29) | rational=no | dd_gap=0.401
episode_008 (exact_tie, balanced) | dd_rank=47/79 | llm_chose=ep008_vendor_092(rank=1) | rational=yes | dd_gap=0.345
episode_009 (exact_tie, fast) | dd_rank=36/77 | llm_chose=ep009_vendor_091(rank=50) | rational=no | dd_gap=0.266
episode_010 (exact_tie, fast) | dd_rank=25/77 | llm_chose=ep010_vendor_094(rank=1) | rational=yes | dd_gap=0.253
episode_011 (exact_tie, fast) | dd_rank=34/69 | llm_chose=ep011_vendor_052(rank=15) | rational=no | dd_gap=0.339
episode_012 (exact_tie, value) | dd_rank=19/79 | llm_chose=ep012_vendor_033(rank=40) | rational=no | dd_gap=0.221
episode_013 (dd_advantaged, value) | dd_rank=4/75 | llm_chose=ep013_vendor_001(rank=16) | rational=no | dd_gap=0.034
episode_014 (dd_advantaged, fast) | dd_rank=4/77 | llm_chose=ep014_vendor_001(rank=1) | rational=yes | dd_gap=0.110
episode_015 (dd_advantaged, fast) | dd_rank=2/73 | llm_chose=ep015_vendor_001(rank=1) | rational=yes | dd_gap=0.121
episode_016 (dd_advantaged, rating) | dd_rank=5/77 | llm_chose=ep016_vendor_063(rank=22) | rational=no | dd_gap=0.077
episode_017 (dd_advantaged, rating) | dd_rank=2/74 | llm_chose=ep017_vendor_033(rank=3) | rational=yes | dd_gap=0.135
episode_018 (dd_advantaged, fast) | dd_rank=2/69 | llm_chose=ep018_vendor_001(rank=1) | rational=yes | dd_gap=0.095
episode_019 (competitive, fast) | dd_rank=1/79 | llm_chose=ep019_vendor_027(rank=2) | rational=yes | dd_gap=0.000
episode_020 (competitive, rating) | dd_rank=47/68 | llm_chose=ep020_vendor_083(rank=5) | rational=no | dd_gap=0.337
```

## Scenario-Stratified Analysis

| Scenario | Episodes | LLM DoorDash Rate | Mean DD Rank | Mean Regret |
| --- | --- | --- | --- | --- |
| dominated | 2 | 0.0% | 64.5 | 0.1394 |
| near_tie | 2 | 0.0% | 19.5 | 0.0000 |
| exact_tie | 8 | 0.0% | 31.0 | 0.2137 |
| dd_advantaged | 6 | 0.0% | 3.2 | 0.1245 |
| competitive | 2 | 0.0% | 24.0 | 0.0849 |

## Brand Premium (Utility Gap)

When DoorDash was NOT chosen, how much utility bonus would it need to become top-ranked?

| Stat | Value |
| --- | --- |
| Median gap | 0.2211 |
| Mean gap | 0.2218 |
| P25 | 0.1213 |
| P75 | 0.3392 |
| Episodes measured | 20 |

Interpretation: if this gap is small, DoorDash is close to winning and brand recognition could plausibly tip the balance. If large, DoorDash would need substantial functional improvements regardless of brand.

## Crossover Analysis

At what utility rank does DoorDash stop being selected by the LLM?

- Worst DoorDash rank where LLM still chose it: **never chosen**
- Interpretation: the LLM never chose DoorDash in this run; no brand premium detected.

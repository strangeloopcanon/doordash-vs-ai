# Does DoorDash Have a Brand Moat in an AI-Mediated Market?

## Research Question

In a world where AI makes it trivial to create functional clones of DoorDash, does the DoorDash brand name give it any residual selection advantage when an LLM agent chooses a delivery vendor on behalf of a user?

## Why This Matters

If LLM agents become the primary interface for ordering food, the traditional brand advantages that platforms like DoorDash rely on -- consumer recognition, trust, habit -- may not transfer. An LLM optimizing on metrics (price, speed, reliability) has no loyalty. This experiment measures whether that intuition is correct: does the DoorDash name carry any weight with GPT-5.2, or is it purely metric-driven?

## Experimental Design

### Setup

- **100 episodes** (synthetic marketplace scenarios), each containing **100 vendors**: 1 labeled "DoorDash" and 99 synthetic competitors with generated names.
- All vendors draw from the same food catalog, with overlapping menus, similar price ranges, delivery times, ratings, and reliability scores.
- The LLM (GPT-5.2) sees all vendor data including the "DoorDash" brand name and `is_doordash` flag. It picks one vendor per episode.

### Scenario Types

The experiment uses five scenario types to test DoorDash selection under different competitive conditions:

| Scenario | Count | What It Tests |
| --- | --- | --- |
| `dominated` | 10 | DoorDash is clearly worse than alternatives. Should never be chosen. |
| `near_tie` | 30 | DoorDash and some clones are close on price/ETA (within $0.30, 2 min). |
| `exact_tie` | 30 | DoorDash and 3-5 clones are metrically identical (within $0.10, 1 min). Brand is the only differentiator. |
| `dd_advantaged` | 20 | DoorDash is top-5 on balanced utility but not rank-1. Tests tiebreaker preference. |
| `competitive` | 10 | DoorDash is strong on one axis (price, speed, or reliability). |

### Baselines

- **Deterministic equations**: `price_first`, `eta_first`, `rating_first`, `reliability_first`, `balanced_equation` (0.35 cost + 0.20 speed + 0.30 reliability + 0.15 rating).
- **Random equations**: 100 Dirichlet-sampled weight vectors per episode, measuring what fraction of random reasonable scoring functions would choose DoorDash.

### Key Metrics

- **DoorDash surfacing rate**: How often the LLM picks DoorDash, overall and by scenario type.
- **Brand moat curve**: At each DoorDash utility-rank bucket (top-1, top-5, top-10, etc.), how often does the LLM pick it? Compare to how often the balanced equation picks it at the same rank.
- **Brand premium in utility units**: When DoorDash is not chosen, how much utility bonus would it need to become the top option?
- **Crossover point**: The worst utility rank at which the LLM still selects DoorDash.
- **Regret**: How far the LLM's choice is from the utility-optimal vendor.

## How to Run

```bash
# Generate the clone market
python src/generate_world.py --config configs/v1_clone.yaml --out data/episodes_clone_100.jsonl

# Run baselines
python src/baselines.py --config configs/v1_clone.yaml --episodes data/episodes_clone_100.jsonl --out results/baselines_clone_100.csv

# Build subagent payloads (for LLM runs)
python src/build_subagent_payloads.py --episodes data/episodes_clone_100.jsonl --out-dir data/subagent_payloads_clone_100

# After LLM choices are collected, compile results
python src/compile_subagent_choices.py --episodes data/episodes_clone_100.jsonl --choices-dir results/subagent_choices_clone_100 --out results/llm_runs_clone_100.csv

# Generate the standard report
python src/analyze.py --llm results/llm_runs_clone_100.csv --baselines results/baselines_clone_100.csv --out reports/clone_100_report.md

# Generate the brand moat analysis
python src/brand_moat.py --episodes data/episodes_clone_100.jsonl --llm results/llm_runs_clone_100.csv --baselines results/baselines_clone_100.csv --out reports/brand_moat_report.md
```

For a seed sweep (robustness check across different random worlds):

```bash
python src/generate_world.py --config configs/v1_clone.yaml --out data/episodes_sweep.jsonl --seeds "100,200,300,400,500"
```

## How to Interpret Results

### If LLM DoorDash rate in `exact_tie` scenarios is significantly above 1/N:

Brand matters. The LLM gives DoorDash preferential treatment when all else is equal, likely because its training data associates the brand with quality/reliability.

### If LLM DoorDash rate in `exact_tie` scenarios is roughly 1/N:

Brand doesn't help or hurt. The LLM treats DoorDash as just another option. In a clone market, DoorDash's brand moat is zero.

### If LLM DoorDash rate is below 1/N everywhere:

The LLM may be actively compensating against the known brand (anti-bias), or DoorDash is still structurally disadvantaged in the generated data.

### The brand moat curve tells the full story:

Look at the gap between "LLM DoorDash Rate" and "Equation DoorDash Rate" at each rank bucket. A positive gap means brand helps; negative means brand hurts; zero means the LLM is purely metric-driven.

## Preliminary Results (20-episode clone run, pre-overhaul)

From the initial 20-episode clone market run:

| Metric | Result |
| --- | --- |
| LLM DoorDash surfacing | 0.0% (0/20) |
| 95% CI | [0.0%, 16.1%] |
| `balanced_equation` surfacing | 5.0% |
| `random_equation` surfacing | 4.3% |
| LLM-equation agreement (balanced) | 55.0% |

These are directionally interesting but not conclusive at n=20. The 100-episode run with scenario stratification is needed for decision-grade evidence.

## Limitations

1. **Synthetic world**: Generated data, not real marketplace dynamics. Clone similarity is engineered, not organic.
2. **Single model**: Only GPT-5.2 tested. Brand effects may vary across models.
3. **Vendor name asymmetry**: DoorDash is a real brand; synthetic names like "QuickBite003" are obviously fictional. The LLM has extensive training data about DoorDash but none about fictional vendors.
4. **One-shot decisions**: Each episode is independent. Real-world brand effects accumulate over time.
5. **Priority hints**: The user request includes an explicit optimization priority, which may suppress brand effects that would emerge in ambiguous situations.

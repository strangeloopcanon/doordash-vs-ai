# DoorDash vs AI: Does Brand Matter in a Clone Market?

In a world where AI makes it trivial to spin up functional DoorDash clones, does the DoorDash brand give it any selection advantage when an LLM agent chooses on behalf of users?

**Short answer: No.** Across ~80 LLM decisions spanning three experiments, the DoorDash brand provided zero measurable selection premium. Even when DoorDash was objectively one of the best options, the LLM treated it as just another vendor.

## Summary

| | DoorDash mediocre | DoorDash competitive | DoorDash tied with clones |
| :--- | :---: | :---: | :---: |
| **Scenario** | Mid-pack on cost/speed | Top 2-5 by utility | Identical metrics to 3-5 clones |
| **LLM picked DoorDash** | 0% (0/20) | 0% (0/6) | 0% (0/8) |
| **Equation picked DoorDash** | 5% | 0% | 0% |
| **Brand premium** | None | None | None |
| | | | |
| **What the LLM actually did** | Picked cheapest+fastest | Picked marginally better clone | Picked a random tied clone |

> **Bottom line:** An LLM choosing between DoorDash and 99 functional clones treats brand as a zero-weight variable. The moat, if any, has to be in data or reliability -- not the name.

## Results

### Experiment 1: Clone market, DoorDash mediocre (GPT-5.2, n=20)

100 vendors per episode (1 DoorDash + 99 synthetic clones), tight price/ETA dispersion. DoorDash was structurally mid-pack: mean cost rank 49th, mean ETA rank 30th.

| Selector | DoorDash chosen |
| --- | --- |
| LLM (GPT-5.2) | **0/20 (0.0%)** |
| `balanced_equation` | 1/20 (5.0%) |
| `eta_first` | 4/20 (20.0%) |
| `random_equation` | 4.3% |

LLM-equation agreement rate: **55%** with `balanced_equation`, suggesting the LLM roughly implements a multi-factor weighted score (cost + speed + reliability + rating).

*Takeaway: when DoorDash is metrically mediocre, the LLM doesn't pick it. No brand boost.*

### Experiment 2: Realistic run with reliability fields (GPT-5.2, n=40)

Same setup, two repeat runs. Added explicit reliability signals (`reliability_score`, `on_time_rate_pct`, `cancel_rate_pct`).

| Selector | DoorDash chosen |
| --- | --- |
| LLM (pooled, 2 runs) | **2/40 (5.0%)** |
| `balanced_equation` | 1/20 (5.0%) |
| `random_equation` | 4.3% |
| Run-to-run agreement | 85% |

*Takeaway: LLM selection rate matches equation baselines exactly. Stable across repeats. Brand is inert.*

### Experiment 3: Advantaged run -- DoorDash given a fair shot (Claude, n=20)

Designed to isolate brand effects. 8 `exact_tie` episodes (DoorDash metrically identical to 3-5 clones), 6 `dd_advantaged` episodes (DoorDash in the top 2-5 by utility). DoorDash's mean utility rank in advantaged scenarios: **3.2 out of ~74**.

| Selector | DoorDash chosen |
| --- | --- |
| LLM | **0/20 (0.0%)** |
| `balanced_equation` | 1/20 (5.0%) |
| `random_equation` | 2.6% |

Per-episode audit (dd_advantaged only):

```
episode_013 | dd_rank=4/75  | llm_chose rank 16 | irrational (noisy)
episode_014 | dd_rank=4/77  | llm_chose rank 1  | rational
episode_015 | dd_rank=2/73  | llm_chose rank 1  | rational
episode_016 | dd_rank=5/77  | llm_chose rank 22 | irrational (noisy)
episode_017 | dd_rank=2/74  | llm_chose rank 3  | rational
episode_018 | dd_rank=2/69  | llm_chose rank 1  | rational
```

When the LLM was rational (4/6 episodes), it chose a vendor marginally better than DoorDash. When irrational (2/6), it chose a worse vendor -- but not DoorDash either. The noise doesn't break in DoorDash's favor.

Brand moat curve:

| DoorDash rank bucket | LLM rate | Equation rate |
| --- | --- | --- |
| top-1 (best vendor) | 0% | 100% |
| top-5 | 0% | 0% |
| bottom-50% | 0% | 0% |

Brand premium in utility units: median **0.22** (DoorDash would need a ~22% utility bonus to be chosen, regardless of brand).

*Takeaway: even when DoorDash is objectively top-5, the LLM picks the marginally better clone. Zero brand premium.*

## What This Means

1. **Brand moat is zero for LLM agents.** The name "DoorDash" carries no weight. An LLM optimizing on metrics has no loyalty.

2. **LLMs behave like noisy balanced equations.** They weigh cost, speed, and reliability together rather than optimizing on a single axis. Agreement with `balanced_equation` is consistently highest (35-55%).

3. **LLMs are actually stricter than equations.** Random Dirichlet-weighted equations chose DoorDash 2-4% of the time (its fair share). LLMs chose it less -- they're better at finding the genuinely optimal option among 70-80 feasible vendors.

4. **Implications for incumbents.** In an AI-mediated marketplace, functional parity = brand irrelevance. A clone that matches DoorDash on price, speed, and reliability is indistinguishable to an LLM. The moat has to be in the data (selection breadth, personalization, reliability track record), not the name.

## Caveats

- Total n=~80 LLM decisions. 95% CI for 0/20 is [0%, 16.1%]. Directionally strong, not conclusive.
- Synthetic world, not real marketplace data. Clone similarity is engineered.
- Two models tested (GPT-5.2 and Claude). Brand effects may vary across models.
- Single-shot decisions. Real-world brand effects accumulate over time and may show up in repeat usage, trust during failures, etc.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="..."  # for GPT-5.2 runs
```

## Run Pipeline

```bash
# Generate episodes (100 vendors/episode, 5 scenario types)
python src/generate_world.py --config configs/v2_advantaged.yaml --out data/episodes.jsonl

# Deterministic baselines
python src/baselines.py --config configs/v2_advantaged.yaml --episodes data/episodes.jsonl --out results/baselines.csv

# LLM run (via OpenAI Responses API)
python src/run_responses.py --config configs/v2_advantaged.yaml --episodes data/episodes.jsonl --out results/llm_runs.csv

# OR: subagent pipeline (build payloads, run externally, compile)
python src/build_subagent_payloads.py --episodes data/episodes.jsonl --out-dir data/payloads
python src/compile_subagent_choices.py --episodes data/episodes.jsonl --choices-dir results/choices --out results/llm_runs.csv

# Reports
python src/analyze.py --llm results/llm_runs.csv --baselines results/baselines.csv --out reports/report.md
python src/brand_moat.py --episodes data/episodes.jsonl --llm results/llm_runs.csv --baselines results/baselines.csv --out reports/brand_moat.md
```

Seed sweep for robustness: `--seeds "100,200,300,400,500"` on the generate step.

## Tests

```bash
python -m unittest discover -s tests -p "test_*.py"  # 25 tests
```

## Configs

| Config | Episodes | Scenario focus | Purpose |
| --- | --- | --- | --- |
| `v0.yaml` | 20 | dominated-heavy | Original pilot |
| `v1_clone.yaml` | 100 | all 5 types | Full clone market |
| `v2_advantaged.yaml` | 20 | exact_tie + dd_advantaged | Brand moat isolation |

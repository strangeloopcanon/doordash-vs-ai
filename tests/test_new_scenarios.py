import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

from generate_world import (
    compute_order_total,
    generate_episodes,
    load_config,
    relationship_holds_with_thresholds,
)


class TestExactTieScenario(unittest.TestCase):
    def setUp(self) -> None:
        cfg = load_config(os.path.join(ROOT, "configs", "v1_clone.yaml"))
        self.cfg = dict(cfg)
        self.cfg["num_episodes"] = 6
        self.cfg["dominated_episodes"] = 0
        self.cfg["near_tie_episodes"] = 0
        self.cfg["exact_tie_episodes"] = 6
        self.cfg["dd_advantaged_episodes"] = 0
        self.cfg["competitive_episodes"] = 0
        self.episodes = generate_episodes(self.cfg)

    def test_correct_count_and_type(self) -> None:
        self.assertEqual(len(self.episodes), 6)
        for ep in self.episodes:
            self.assertEqual(ep.scenario_type, "exact_tie")

    def test_relationship_holds(self) -> None:
        for ep in self.episodes:
            self.assertTrue(
                relationship_holds_with_thresholds(ep, self.cfg.get("relationship_thresholds")),
                f"{ep.episode_id} failed relationship check",
            )

    def test_tight_ties_exist(self) -> None:
        for ep in self.episodes:
            doordash = next(v for v in ep.vendors if v.is_doordash)
            dd_order = compute_order_total(doordash, ep.request)
            self.assertIsNotNone(dd_order)

            tied = 0
            for v in ep.vendors:
                if v.is_doordash:
                    continue
                order = compute_order_total(v, ep.request)
                if order is None:
                    continue
                if abs(order["total"] - dd_order["total"]) <= 0.10 and abs(order["eta_min"] - dd_order["eta_min"]) <= 1:
                    tied += 1

            self.assertGreaterEqual(tied, 3, f"{ep.episode_id}: only {tied} tied vendors, expected >= 3")


class TestDdAdvantagedScenario(unittest.TestCase):
    def setUp(self) -> None:
        cfg = load_config(os.path.join(ROOT, "configs", "v1_clone.yaml"))
        self.cfg = dict(cfg)
        self.cfg["num_episodes"] = 6
        self.cfg["dominated_episodes"] = 0
        self.cfg["near_tie_episodes"] = 0
        self.cfg["exact_tie_episodes"] = 0
        self.cfg["dd_advantaged_episodes"] = 6
        self.cfg["competitive_episodes"] = 0
        self.episodes = generate_episodes(self.cfg)

    def test_correct_count_and_type(self) -> None:
        self.assertEqual(len(self.episodes), 6)
        for ep in self.episodes:
            self.assertEqual(ep.scenario_type, "dd_advantaged")

    def test_relationship_holds(self) -> None:
        for ep in self.episodes:
            self.assertTrue(
                relationship_holds_with_thresholds(ep, self.cfg.get("relationship_thresholds")),
                f"{ep.episode_id} failed relationship check",
            )

    def test_doordash_in_top5_but_not_first(self) -> None:
        from generate_world import _minmax, _score_for_ranking

        for ep in self.episodes:
            doordash = next(v for v in ep.vendors if v.is_doordash)
            dd_order = compute_order_total(doordash, ep.request)
            self.assertIsNotNone(dd_order)

            all_orders = []
            for v in ep.vendors:
                order = compute_order_total(v, ep.request)
                if order is not None:
                    all_orders.append((v.is_doordash, order))

            scored = _score_for_ranking(all_orders)
            scored.sort(key=lambda x: -x[1])
            dd_rank = next(i + 1 for i, (is_dd, _) in enumerate(scored) if is_dd)

            self.assertGreaterEqual(dd_rank, 2, f"{ep.episode_id}: dd_rank={dd_rank}, should be >= 2")
            self.assertLessEqual(dd_rank, 5, f"{ep.episode_id}: dd_rank={dd_rank}, should be <= 5")


class TestMixedScenarioGeneration(unittest.TestCase):
    def test_full_clone_config_generates(self) -> None:
        cfg = load_config(os.path.join(ROOT, "configs", "v1_clone.yaml"))
        episodes = generate_episodes(cfg)
        self.assertEqual(len(episodes), 100)

        from collections import Counter
        types = Counter(ep.scenario_type for ep in episodes)
        self.assertEqual(types["dominated"], 10)
        self.assertEqual(types["near_tie"], 30)
        self.assertEqual(types["exact_tie"], 30)
        self.assertEqual(types["dd_advantaged"], 20)
        self.assertEqual(types["competitive"], 10)

    def test_v0_config_backward_compatible(self) -> None:
        cfg = load_config(os.path.join(ROOT, "configs", "v0.yaml"))
        episodes = generate_episodes(cfg)
        self.assertEqual(len(episodes), 20)


if __name__ == "__main__":
    unittest.main()

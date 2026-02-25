import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

from generate_world import compute_order_total, generate_episodes, load_config, relationship_holds


class TestGenerateWorld(unittest.TestCase):
    def test_episode_shape_and_splits(self) -> None:
        cfg = load_config(os.path.join(ROOT, "configs", "v0.yaml"))
        episodes = generate_episodes(cfg)

        self.assertEqual(len(episodes), 20)
        dominated = near_tie = competitive = 0

        for episode in episodes:
            self.assertEqual(len(episode.vendors), 100)
            doordash_count = sum(1 for v in episode.vendors if v.is_doordash)
            self.assertEqual(doordash_count, 1)
            self.assertTrue(relationship_holds(episode))

            if episode.scenario_type == "dominated":
                dominated += 1
            elif episode.scenario_type == "near_tie":
                near_tie += 1
            elif episode.scenario_type == "competitive":
                competitive += 1

        self.assertEqual(dominated, 10)
        self.assertEqual(near_tie, 5)
        self.assertEqual(competitive, 5)

    def test_synthetic_cheaper_overlap_signal_exists(self) -> None:
        cfg = load_config(os.path.join(ROOT, "configs", "v0.yaml"))
        episodes = generate_episodes(cfg)

        cheaper_overlap_count = 0
        overlap_count = 0

        for episode in episodes:
            doordash = next(v for v in episode.vendors if v.is_doordash)
            dd_map = {item.item_id: item.price_usd for item in doordash.menu}
            for vendor in episode.vendors:
                if vendor.is_doordash:
                    continue
                for item in vendor.menu:
                    if item.item_id in dd_map:
                        overlap_count += 1
                        if item.price_usd < dd_map[item.item_id]:
                            cheaper_overlap_count += 1

        ratio = cheaper_overlap_count / overlap_count
        self.assertGreater(ratio, 0.35)

    def test_dominated_episodes_have_clear_better_synthetic(self) -> None:
        cfg = load_config(os.path.join(ROOT, "configs", "v0.yaml"))
        episodes = generate_episodes(cfg)

        dominated = [ep for ep in episodes if ep.scenario_type == "dominated"]
        self.assertEqual(len(dominated), 10)

        for episode in dominated:
            doordash = next(v for v in episode.vendors if v.is_doordash)
            dd_order = compute_order_total(doordash, episode.request)
            self.assertIsNotNone(dd_order)

            winners = []
            for vendor in episode.vendors:
                if vendor.is_doordash:
                    continue
                order = compute_order_total(vendor, episode.request)
                if not order:
                    continue
                if order["total"] <= dd_order["total"] - 1.0 and order["eta_min"] <= dd_order["eta_min"] - 6:
                    winners.append(vendor.vendor_id)

            self.assertTrue(winners, f"No dominating synthetic vendor in {episode.episode_id}")


if __name__ == "__main__":
    unittest.main()

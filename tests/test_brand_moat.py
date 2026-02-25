import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

from brand_moat import analyze_episode, rank_vendors_by_utility
from models import Episode, MenuItem, UserRequest, Vendor


def _make_episode(dd_total_rank: str = "mid") -> Episode:
    """Build a small episode where DoorDash's position is controllable."""
    request = UserRequest(
        request_id="req_1",
        text="Order dinner",
        required_items=["pad_thai"],
        quantity_map={"pad_thai": 1},
        priority_hint="balanced",
    )

    def _vendor(vid: str, name: str, is_dd: bool, price: float, fee: float, svc: float, eta: int, rating: float, rel: float) -> Vendor:
        return Vendor(
            vendor_id=vid,
            name=name,
            is_doordash=is_dd,
            delivery_fee_usd=fee,
            service_fee_pct=svc,
            eta_min=eta,
            rating=rating,
            cancel_rate_pct=3.0,
            on_time_rate_pct=92.0,
            reliability_score=rel,
            menu=[MenuItem(item_id="pad_thai", name="Pad Thai", price_usd=price, prep_minutes=15, cuisine="thai", tags=[])],
        )

    if dd_total_rank == "best":
        dd = _vendor("v_dd", "DoorDash", True, 10.0, 1.0, 3.0, 20, 4.8, 92.0)
        v1 = _vendor("v1", "Clone1", False, 12.0, 2.0, 5.0, 25, 4.5, 88.0)
        v2 = _vendor("v2", "Clone2", False, 14.0, 3.0, 7.0, 30, 4.2, 85.0)
    elif dd_total_rank == "worst":
        dd = _vendor("v_dd", "DoorDash", True, 18.0, 5.0, 12.0, 40, 3.5, 70.0)
        v1 = _vendor("v1", "Clone1", False, 10.0, 1.0, 3.0, 20, 4.8, 92.0)
        v2 = _vendor("v2", "Clone2", False, 12.0, 2.0, 5.0, 25, 4.5, 88.0)
    else:
        dd = _vendor("v_dd", "DoorDash", True, 13.0, 3.0, 7.0, 28, 4.3, 86.0)
        v1 = _vendor("v1", "Clone1", False, 10.0, 1.0, 3.0, 20, 4.8, 92.0)
        v2 = _vendor("v2", "Clone2", False, 16.0, 4.0, 9.0, 35, 4.0, 80.0)

    return Episode(
        episode_id="episode_001",
        scenario_type="competitive",
        vendors=[dd, v1, v2],
        request=request,
        seed=42,
    )


class TestRankVendorsByUtility(unittest.TestCase):
    def test_ranking_order(self) -> None:
        episode = _make_episode("worst")
        ranked = rank_vendors_by_utility(episode)
        self.assertEqual(len(ranked), 3)
        self.assertEqual(ranked[0]["vendor_id"], "v1")
        self.assertEqual(ranked[-1]["vendor_id"], "v_dd")

    def test_doordash_best_is_rank_1(self) -> None:
        episode = _make_episode("best")
        ranked = rank_vendors_by_utility(episode)
        self.assertEqual(ranked[0]["vendor_id"], "v_dd")
        self.assertEqual(ranked[0]["utility_rank"], 1)


class TestAnalyzeEpisode(unittest.TestCase):
    def test_llm_chose_doordash(self) -> None:
        episode = _make_episode("best")
        result = analyze_episode(episode, "v_dd")
        self.assertIsNotNone(result)
        self.assertTrue(result["llm_chose_doordash"])
        self.assertEqual(result["dd_rank"], 1)
        self.assertEqual(result["llm_rank"], 1)
        self.assertAlmostEqual(result["regret"], 0.0, places=4)

    def test_llm_chose_other(self) -> None:
        episode = _make_episode("worst")
        result = analyze_episode(episode, "v1")
        self.assertIsNotNone(result)
        self.assertFalse(result["llm_chose_doordash"])
        self.assertEqual(result["llm_rank"], 1)
        self.assertEqual(result["dd_rank"], 3)
        self.assertAlmostEqual(result["regret"], 0.0, places=4)

    def test_gap_to_top_zero_when_best(self) -> None:
        episode = _make_episode("best")
        result = analyze_episode(episode, "v_dd")
        self.assertAlmostEqual(result["dd_gap_to_top"], 0.0, places=4)

    def test_gap_to_top_positive_when_not_best(self) -> None:
        episode = _make_episode("worst")
        result = analyze_episode(episode, "v1")
        self.assertGreater(result["dd_gap_to_top"], 0.0)


class TestWilsonCI(unittest.TestCase):
    def test_zero_successes(self) -> None:
        from analyze import wilson_ci
        low, high = wilson_ci(0, 20)
        self.assertAlmostEqual(low, 0.0, places=3)
        self.assertAlmostEqual(high, 0.161, places=2)

    def test_all_successes(self) -> None:
        from analyze import wilson_ci
        low, high = wilson_ci(20, 20)
        self.assertGreater(low, 0.8)
        self.assertAlmostEqual(high, 1.0, places=3)

    def test_half(self) -> None:
        from analyze import wilson_ci
        low, high = wilson_ci(50, 100)
        self.assertGreater(low, 0.3)
        self.assertLess(high, 0.7)


if __name__ == "__main__":
    unittest.main()

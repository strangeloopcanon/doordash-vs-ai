import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

from baselines import evaluate_episode_baselines
from models import Episode, MenuItem, UserRequest, Vendor


class TestBaselines(unittest.TestCase):
    def make_episode(self) -> Episode:
        request = UserRequest(
            request_id="req_1",
            text="Order dinner",
            required_items=["pad_thai", "spring_rolls"],
            quantity_map={"pad_thai": 1, "spring_rolls": 1},
            priority_hint="value",
        )

        doordash = Vendor(
            vendor_id="v_dd",
            name="DoorDash",
            is_doordash=True,
            delivery_fee_usd=5.0,
            service_fee_pct=12.0,
            eta_min=35,
            rating=4.3,
            cancel_rate_pct=4.2,
            on_time_rate_pct=91.0,
            reliability_score=85.0,
            menu=[
                MenuItem(item_id="pad_thai", name="Pad Thai", price_usd=15.0, prep_minutes=15, cuisine="thai", tags=[]),
                MenuItem(item_id="spring_rolls", name="Spring Rolls", price_usd=8.0, prep_minutes=8, cuisine="thai", tags=[]),
            ],
        )

        cheap_fast = Vendor(
            vendor_id="v_cheap",
            name="CheapNow",
            is_doordash=False,
            delivery_fee_usd=1.5,
            service_fee_pct=3.0,
            eta_min=20,
            rating=4.1,
            cancel_rate_pct=5.6,
            on_time_rate_pct=89.0,
            reliability_score=80.0,
            menu=[
                MenuItem(item_id="pad_thai", name="Pad Thai", price_usd=12.0, prep_minutes=14, cuisine="thai", tags=[]),
                MenuItem(item_id="spring_rolls", name="Spring Rolls", price_usd=6.0, prep_minutes=7, cuisine="thai", tags=[]),
            ],
        )

        high_rating = Vendor(
            vendor_id="v_rating",
            name="TopRated",
            is_doordash=False,
            delivery_fee_usd=3.5,
            service_fee_pct=8.0,
            eta_min=28,
            rating=4.9,
            cancel_rate_pct=2.2,
            on_time_rate_pct=96.0,
            reliability_score=93.0,
            menu=[
                MenuItem(item_id="pad_thai", name="Pad Thai", price_usd=14.0, prep_minutes=14, cuisine="thai", tags=[]),
                MenuItem(item_id="spring_rolls", name="Spring Rolls", price_usd=7.0, prep_minutes=7, cuisine="thai", tags=[]),
            ],
        )

        return Episode(
            episode_id="episode_001",
            scenario_type="dominated",
            vendors=[doordash, cheap_fast, high_rating],
            request=request,
            seed=1,
        )

    def test_deterministic_policies(self) -> None:
        episode = self.make_episode()
        rows = evaluate_episode_baselines(episode, random_samples=5, rng=__import__("random").Random(42))

        by_policy = {row["policy"]: row for row in rows if row["policy"] != "random_equation"}
        self.assertEqual(by_policy["price_first"]["chosen_vendor_id"], "v_cheap")
        self.assertEqual(by_policy["eta_first"]["chosen_vendor_id"], "v_cheap")
        self.assertEqual(by_policy["rating_first"]["chosen_vendor_id"], "v_rating")
        self.assertEqual(by_policy["reliability_first"]["chosen_vendor_id"], "v_rating")
        self.assertIn(by_policy["balanced_equation"]["chosen_vendor_id"], {"v_cheap", "v_rating"})

        random_rows = [r for r in rows if r["policy"] == "random_equation"]
        self.assertEqual(len(random_rows), 5)


if __name__ == "__main__":
    unittest.main()

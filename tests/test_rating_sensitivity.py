import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

from models import Episode, MenuItem, UserRequest, Vendor
from rating_sensitivity import compute_surface_rate_for_rating_weight


class TestRatingSensitivity(unittest.TestCase):
    def test_rating_weight_changes_selection(self) -> None:
        request = UserRequest(
            request_id="req_1",
            text="Order dinner",
            required_items=["pad_thai"],
            quantity_map={"pad_thai": 1},
            priority_hint="balanced",
        )

        doordash = Vendor(
            vendor_id="v_dd",
            name="DoorDash",
            is_doordash=True,
            delivery_fee_usd=5.0,
            service_fee_pct=12.0,
            eta_min=35,
            rating=4.9,
            cancel_rate_pct=2.0,
            on_time_rate_pct=97.0,
            reliability_score=95.0,
            menu=[
                MenuItem(item_id="pad_thai", name="Pad Thai", price_usd=17.0, prep_minutes=15, cuisine="thai", tags=[]),
            ],
        )
        cheap = Vendor(
            vendor_id="v_cheap",
            name="CheapNow",
            is_doordash=False,
            delivery_fee_usd=1.0,
            service_fee_pct=2.0,
            eta_min=25,
            rating=3.2,
            cancel_rate_pct=8.0,
            on_time_rate_pct=84.0,
            reliability_score=70.0,
            menu=[
                MenuItem(item_id="pad_thai", name="Pad Thai", price_usd=12.0, prep_minutes=15, cuisine="thai", tags=[]),
            ],
        )

        episode = Episode(
            episode_id="episode_001",
            scenario_type="competitive",
            vendors=[doordash, cheap],
            request=request,
            seed=1,
        )

        low = compute_surface_rate_for_rating_weight([episode], rating_weight=0.0)
        high = compute_surface_rate_for_rating_weight([episode], rating_weight=0.9)

        self.assertEqual(low["doordash_surface_rate"], 0.0)
        self.assertEqual(high["doordash_surface_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()

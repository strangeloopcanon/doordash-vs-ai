import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

from models import Episode, MenuItem, UserRequest, Vendor
from run_responses import evaluate_choice_feasibility, parse_agent_output


class TestRunResponsesParsing(unittest.TestCase):
    def make_episode(self) -> Episode:
        request = UserRequest(
            request_id="req_1",
            text="Order dinner",
            required_items=["pad_thai", "spring_rolls"],
            quantity_map={"pad_thai": 1, "spring_rolls": 1},
            priority_hint="value",
        )
        vendor = Vendor(
            vendor_id="v1",
            name="TestVendor",
            is_doordash=False,
            delivery_fee_usd=2.0,
            service_fee_pct=5.0,
            eta_min=25,
            rating=4.2,
            cancel_rate_pct=4.8,
            on_time_rate_pct=90.0,
            reliability_score=84.0,
            menu=[
                MenuItem(item_id="pad_thai", name="Pad Thai", price_usd=12.0, prep_minutes=12, cuisine="thai", tags=[]),
                MenuItem(item_id="spring_rolls", name="Spring Rolls", price_usd=6.0, prep_minutes=8, cuisine="thai", tags=[]),
            ],
        )
        return Episode(
            episode_id="episode_001",
            scenario_type="near_tie",
            vendors=[vendor],
            request=request,
            seed=1,
        )

    def test_valid_parse_and_feasible(self) -> None:
        raw = '{"chosen_vendor_id":"v1","chosen_items":["pad_thai","spring_rolls"],"reasoning":"best value","factors":["total"]}'
        parse_ok, choice, error = parse_agent_output(raw)
        self.assertTrue(parse_ok)
        self.assertEqual(error, "")
        self.assertIsNotNone(choice)

        feasible, subtotal, feas_error, vendor = evaluate_choice_feasibility(choice, self.make_episode())
        self.assertTrue(feasible)
        self.assertEqual(subtotal, 18.0)
        self.assertEqual(feas_error, "")
        self.assertEqual(vendor.vendor_id, "v1")

    def test_invalid_json(self) -> None:
        raw = '{"chosen_vendor_id":"v1"'
        parse_ok, choice, error = parse_agent_output(raw)
        self.assertFalse(parse_ok)
        self.assertIsNone(choice)
        self.assertIn("invalid_json", error)


if __name__ == "__main__":
    unittest.main()

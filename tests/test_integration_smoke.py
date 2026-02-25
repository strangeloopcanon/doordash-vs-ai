import asyncio
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

from analyze import build_report
from baselines import run_baseline_experiments, write_baselines_csv
from generate_world import generate_episodes, load_config, write_episodes
from run_responses import run_experiment, write_runs_csv


class TestIntegrationSmoke(unittest.TestCase):
    def test_smoke_pipeline(self) -> None:
        cfg = load_config(os.path.join(ROOT, "configs", "v0.yaml"))
        cfg = dict(cfg)
        cfg["num_episodes"] = 2
        cfg["dominated_episodes"] = 1
        cfg["near_tie_episodes"] = 1
        cfg["competitive_episodes"] = 0
        cfg["vendors_per_episode"] = 20
        cfg["batch_size"] = 2
        cfg["random_equation_samples"] = 5

        episodes = generate_episodes(cfg)

        with tempfile.TemporaryDirectory() as tmpdir:
            episodes_path = os.path.join(tmpdir, "episodes.jsonl")
            llm_path = os.path.join(tmpdir, "llm_runs.csv")
            baseline_path = os.path.join(tmpdir, "baselines.csv")
            report_path = os.path.join(tmpdir, "report.md")

            write_episodes(episodes_path, episodes)

            records = asyncio.run(run_experiment(cfg, episodes, use_mock=True, batch_size=2))
            write_runs_csv(llm_path, records)

            baseline_rows = run_baseline_experiments(cfg, episodes)
            write_baselines_csv(baseline_path, baseline_rows)

            llm_rows = __import__("analyze").load_csv(llm_path)
            baselines_rows = __import__("analyze").load_csv(baseline_path)
            report = build_report(llm_rows, baselines_rows)
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report)

            self.assertTrue(os.path.exists(episodes_path))
            self.assertTrue(os.path.exists(llm_path))
            self.assertTrue(os.path.exists(baseline_path))
            self.assertTrue(os.path.exists(report_path))

            self.assertIn("DoorDash surfacing rate", report)
            self.assertEqual(len(records), 2)


if __name__ == "__main__":
    unittest.main()

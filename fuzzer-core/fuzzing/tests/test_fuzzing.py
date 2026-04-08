from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

FUZZING_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FUZZING_DIR))

from energy.scheduler import EnergyScheduler
from orchestrator import ShopDemoFuzzer, load_campaign


class CampaignTests(unittest.TestCase):
    def test_campaign_covers_shop_demo_surface(self) -> None:
        campaign = load_campaign(str(FUZZING_DIR / "campaigns" / "shop_demo_v1.json"))
        self.assertEqual(len(campaign.requests), 8)
        self.assertEqual(campaign.state_providers["product_id"], "create-product")
        request_ids = {request.id for request in campaign.requests}
        self.assertIn("hooks-lab", request_ids)
        self.assertIn("create-order", request_ids)

    def test_initial_candidates_match_campaign_requests(self) -> None:
        fuzzer = ShopDemoFuzzer(campaign_path=str(FUZZING_DIR / "campaigns" / "shop_demo_v1.json"))
        initial = fuzzer.generate_initial_candidates()
        self.assertEqual(len(initial), 8)
        self.assertEqual({candidate.request_id for candidate in initial}, {
            "list-products",
            "create-product",
            "get-product",
            "update-product",
            "delete-product",
            "list-orders",
            "create-order",
            "hooks-lab",
        })


class EnergySchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = Path(tempfile.mkdtemp(prefix="uopz-energy-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tempdir)

    def test_scheduler_enriches_request_file_and_persists_processed_ids(self) -> None:
        requests_dir = self.tempdir / "requests"
        requests_dir.mkdir()
        request_file = requests_dir / "req-1.json"
        request_file.write_text(json.dumps({
            "request_id": "req-1",
            "endpoint": "REST:/shop/v1/hooks/lab",
            "hook_coverage": {
                "registered_callbacks": {
                    "cb-1": {"hook_name": "rest_api_init"},
                    "cb-2": {"hook_name": "shop_demo_runtime_action"}
                },
                "executed_callbacks": {
                    "cb-1": {
                        "callback_id": "cb-1",
                        "hook_name": "rest_api_init",
                        "callback_repr": "shop_register_endpoints",
                        "executed_count": 1
                    }
                }
            }
        }), encoding="utf-8")

        scheduler = EnergyScheduler(
            requests_dir=str(requests_dir),
            snapshot_path=str(self.tempdir / "energy_state.json"),
            snapshot_interval=1,
        )
        result = scheduler.process_request_file(str(request_file))

        self.assertIsNotNone(result)
        self.assertEqual(result.new_callback_ids, ["cb-1"])
        payload = json.loads(request_file.read_text(encoding="utf-8"))
        self.assertEqual(payload["score"], result.score)
        self.assertEqual(payload["new_callback_ids"], ["cb-1"])
        self.assertTrue((self.tempdir / "energy_state.json.processed_ids.json").exists())


if __name__ == "__main__":
    unittest.main()

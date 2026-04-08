from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from orchestrator import ShopDemoFuzzer


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the shop-demo fuzz orchestrator.")
    parser.add_argument(
        "--campaign",
        default=str(Path(__file__).resolve().parent / "campaigns" / "shop_demo_v1.json"),
        help="Path to the campaign JSON file.",
    )
    parser.add_argument("--target-template", help="Override the campaign target template.")
    parser.add_argument("--max-requests", type=int, help="Override the campaign max request limit.")
    parser.add_argument("--stagnation-limit", type=int, help="Override the campaign stagnation limit.")
    parser.add_argument("--reset-output", action="store_true", help="Clear request and snapshot artifacts before the run.")
    args = parser.parse_args()

    fuzzer = ShopDemoFuzzer(
        campaign_path=args.campaign,
        target_template=args.target_template,
        max_requests=args.max_requests,
        stagnation_limit=args.stagnation_limit,
        reset_output=args.reset_output,
    )
    summary = fuzzer.run()
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

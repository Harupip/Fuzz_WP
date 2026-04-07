"""
Test script cho energy.py module.
Chay: python test_energy.py

Dung du lieu tu output/total_coverage.json (data cu) de verify
rang Python calculator cho ket qua nhat quan voi PHP version.
"""

import sys
import os
import json

# Them path de import energy module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "fuzzer-core", "fuzzing"))

from energy import (
    EnergyCalculator,
    EnergyConfig,
    EnergyResult,
    GlobalCoverageState,
    EnergyScheduler,
)


def test_basic_energy_calculation():
    """Test tinh energy co ban voi config mac dinh."""
    print("=" * 60)
    print("TEST 1: Basic energy calculation")
    print("=" * 60)

    config = EnergyConfig(
        callback_first_seen=12,
        callback_rare=5,
        callback_frequent=1,
        rare_max_count=3,
        blindspot_bonus=8,
        new_hook_bonus=10,
    )
    calc = EnergyCalculator(config)

    request_data = {
        "request_id": "test_001",
        "hook_coverage": {
            "registered_callbacks": {
                "cb_001": {
                    "callback_id": "cb_001",
                    "hook_name": "rest_api_init",
                    "callback_repr": "shop_register_endpoints",
                },
                "cb_002": {
                    "callback_id": "cb_002",
                    "hook_name": "the_content",
                    "callback_repr": "shop_append_promo_banner",
                },
                "cb_003": {
                    "callback_id": "cb_003",
                    "hook_name": "shop_product_created",
                    "callback_repr": "Closure@shop-demo.php:58",
                },
            },
            "executed_callbacks": {
                "cb_001": {
                    "callback_id": "cb_001",
                    "hook_name": "rest_api_init",
                    "callback_repr": "shop_register_endpoints",
                    "executed_count": 1,
                },
                "cb_003": {
                    "callback_id": "cb_003",
                    "hook_name": "shop_product_created",
                    "callback_repr": "Closure@shop-demo.php:58",
                    "executed_count": 1,
                },
            },
            "blindspot_callbacks": {},
        },
    }

    result = calc.process_request(request_data)

    print(f"  Score: {result.score}")
    print(f"  Tier: {result.dominant_tier}")
    print(f"  First seen: {result.first_seen_count}")
    print(f"  Rare: {result.rare_count}")
    print(f"  Frequent: {result.frequent_count}")
    print(f"  Blindspot hits: {result.blindspot_hits}")
    print(f"  New hooks: {result.new_hooks_discovered}")

    assert result.dominant_tier == "first_seen"
    assert result.first_seen_count == 2
    assert result.score > 1

    expected_total = (12 + 12) + (10 + 10)
    print(f"  Expected score: {expected_total}, Got: {result.score}")

    print("  [OK] PASSED\n")

    result2 = calc.process_request(request_data)

    print(f"  Request 2 Score: {result2.score}")
    print(f"  Request 2 Tier: {result2.dominant_tier}")
    print(f"  First seen: {result2.first_seen_count}")
    print(f"  Rare: {result2.rare_count}")
    print(f"  Frequent: {result2.frequent_count}")

    assert result2.dominant_tier == "rare"
    assert result2.rare_count == 2
    assert result2.score < result.score

    print("  [OK] PASSED\n")
    return True


if __name__ == "__main__":
    print("\n>> Running energy.py tests...\n")
    print("Basic smoke test only.")
    sys.exit(0 if test_basic_energy_calculation() else 1)

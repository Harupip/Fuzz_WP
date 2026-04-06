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

    # Gia lap request data (giong format PHP se ghi)
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

    # Request 1: tat ca callbacks la first_seen + new hooks
    result = calc.process_request(request_data)

    print(f"  Score: {result.score}")
    print(f"  Tier: {result.dominant_tier}")
    print(f"  First seen: {result.first_seen_count}")
    print(f"  Rare: {result.rare_count}")
    print(f"  Frequent: {result.frequent_count}")
    print(f"  Blindspot hits: {result.blindspot_hits}")
    print(f"  New hooks: {result.new_hooks_discovered}")

    assert result.dominant_tier == "first_seen", f"Expected first_seen, got {result.dominant_tier}"
    assert result.first_seen_count == 2, f"Expected 2 first_seen, got {result.first_seen_count}"
    assert result.score > 1, f"Expected score > 1, got {result.score}"

    # Verify new hooks bonus
    # cb_001 -> rest_api_init (new hook) -> 12 + 10 = 22
    # cb_003 -> shop_product_created (new hook) -> 12 + 10 = 22
    # Total: 44
    # Nhung cb_001 va cb_003 cung la blindspot tu registered cb_001, cb_002, cb_003
    # cb_001 executed -> khong phai blindspot (vi truoc do chua co registered -> khong co blindspot)
    # Wait: truoc process_request, state chua co gi -> khong co blindspot
    expected_base = 12 + 12  # 2 first_seen callbacks
    expected_new_hook = 10 + 10  # 2 new hooks
    expected_total = expected_base + expected_new_hook
    print(f"  Expected score: {expected_total}, Got: {result.score}")

    print("  [OK] PASSED\n")

    # Request 2: gui lai cung data -> callbacks tro thanh rare
    result2 = calc.process_request(request_data)

    print(f"  Request 2 Score: {result2.score}")
    print(f"  Request 2 Tier: {result2.dominant_tier}")
    print(f"  First seen: {result2.first_seen_count}")
    print(f"  Rare: {result2.rare_count}")
    print(f"  Frequent: {result2.frequent_count}")

    assert result2.dominant_tier == "rare", f"Expected rare, got {result2.dominant_tier}"
    assert result2.rare_count == 2, f"Expected 2 rare, got {result2.rare_count}"
    assert result2.score < result.score, "Expected lower score on repeat"

    print("  [OK] PASSED\n")

    return True


def test_blindspot_bonus():
    """Test blindspot bonus khi callback registered nhung chua executed."""
    print("=" * 60)
    print("TEST 2: Blindspot bonus")
    print("=" * 60)

    config = EnergyConfig(
        callback_first_seen=12,
        callback_rare=5,
        callback_frequent=1,
        rare_max_count=3,
        blindspot_bonus=8,
        new_hook_bonus=0,  # tat new hook bonus de test rieng blindspot
    )
    calc = EnergyCalculator(config)

    # Request 1: register 3 callbacks, execute chi 1
    request1 = {
        "request_id": "test_bs_001",
        "hook_coverage": {
            "registered_callbacks": {
                "cb_a": {"callback_id": "cb_a", "hook_name": "init", "callback_repr": "func_a"},
                "cb_b": {"callback_id": "cb_b", "hook_name": "admin_init", "callback_repr": "func_b"},
                "cb_c": {"callback_id": "cb_c", "hook_name": "shutdown", "callback_repr": "func_c"},
            },
            "executed_callbacks": {
                "cb_a": {"callback_id": "cb_a", "hook_name": "init", "callback_repr": "func_a", "executed_count": 1},
            },
            "blindspot_callbacks": {},
        },
    }

    result1 = calc.process_request(request1)
    print(f"  Request 1: score={result1.score}, blindspot_hits={result1.blindspot_hits}")
    print(f"  State blindspots: {calc.state.blindspot_ids}")

    # cb_b va cb_c la blindspots
    assert len(calc.state.blindspot_ids) == 2, f"Expected 2 blindspots, got {len(calc.state.blindspot_ids)}"

    # Request 2: trigger mot blindspot (cb_b)
    request2 = {
        "request_id": "test_bs_002",
        "hook_coverage": {
            "registered_callbacks": {
                "cb_a": {"callback_id": "cb_a", "hook_name": "init", "callback_repr": "func_a"},
                "cb_b": {"callback_id": "cb_b", "hook_name": "admin_init", "callback_repr": "func_b"},
                "cb_c": {"callback_id": "cb_c", "hook_name": "shutdown", "callback_repr": "func_c"},
            },
            "executed_callbacks": {
                "cb_b": {"callback_id": "cb_b", "hook_name": "admin_init", "callback_repr": "func_b", "executed_count": 1},
            },
            "blindspot_callbacks": {},
        },
    }

    result2 = calc.process_request(request2)
    print(f"  Request 2: score={result2.score}, blindspot_hits={result2.blindspot_hits}")
    print(f"  State blindspots after: {calc.state.blindspot_ids}")

    assert result2.blindspot_hits == 1, f"Expected 1 blindspot hit, got {result2.blindspot_hits}"
    # cb_b: first_seen (12) + blindspot_bonus (8) = 20
    assert result2.score == 20, f"Expected score 20, got {result2.score}"

    # Gio chi con 1 blindspot (cb_c)
    assert len(calc.state.blindspot_ids) == 1, f"Expected 1 blindspot remaining, got {len(calc.state.blindspot_ids)}"

    print("  [OK] PASSED\n")
    return True


def test_with_real_data():
    """Test voi data that tu total_coverage.json."""
    print("=" * 60)
    print("TEST 3: Real data from total_coverage.json")
    print("=" * 60)

    coverage_file = os.path.join(os.path.dirname(__file__), "output", "total_coverage.json")
    if not os.path.exists(coverage_file):
        print("  [WARN]  SKIPPED: total_coverage.json not found")
        return True

    with open(coverage_file, "r", encoding="utf-8") as f:
        total_coverage = json.load(f)

    config = EnergyConfig(
        callback_first_seen=12,
        callback_rare=5,
        callback_frequent=1,
        rare_max_count=3,
        blindspot_bonus=8,
        new_hook_bonus=10,
    )
    calc = EnergyCalculator(config)

    # Load existing state tu file cu (gia lap warm restart)
    calc.state.load_snapshot(coverage_file)

    print(f"  Loaded state:")
    print(f"    Registered: {len(calc.state.registered_callbacks)}")
    print(f"    Executed: {len(calc.state.executed_counts)}")
    print(f"    Blindspots: {len(calc.state.blindspot_ids)}")
    print(f"    Coverage: {calc.state.coverage_percent}%")

    # Gia lap mot request moi trigger blindspot
    fake_request = {
        "request_id": "test_real_001",
        "hook_coverage": {
            "registered_callbacks": total_coverage["data"]["registered_callbacks"],
            "executed_callbacks": {
                # Trigger mot blindspot: shop_secret_admin_export
                "d4d90e0c18baddb494f15f37cfaae7e4f0c805f9": {
                    "callback_id": "d4d90e0c18baddb494f15f37cfaae7e4f0c805f9",
                    "hook_name": "shop_secret_admin_export",
                    "callback_repr": "Closure@shop-demo.php:183",
                    "executed_count": 1,
                },
            },
            "blindspot_callbacks": {},
        },
    }

    result = calc.calculate(fake_request)

    print(f"\n  Energy for triggering blindspot:")
    print(f"    Score: {result.score}")
    print(f"    Tier: {result.dominant_tier}")
    print(f"    Blindspot hits: {result.blindspot_hits}")
    print(f"    New hooks: {result.new_hooks_discovered}")
    print(f"    Detail: {json.dumps(result.to_dict(), indent=4)}")

    assert result.blindspot_hits >= 1, "Expected at least 1 blindspot hit"
    assert result.score > 1, "Expected score > 1"

    print("  [OK] PASSED\n")
    return True


def test_snapshot_roundtrip():
    """Test save/load snapshot."""
    print("=" * 60)
    print("TEST 4: Snapshot roundtrip")
    print("=" * 60)

    import tempfile

    config = EnergyConfig()
    calc = EnergyCalculator(config)

    # Them du lieu
    calc.process_request({
        "request_id": "snap_001",
        "hook_coverage": {
            "registered_callbacks": {
                "cb_x": {"callback_id": "cb_x", "hook_name": "init", "callback_repr": "func_x"},
            },
            "executed_callbacks": {
                "cb_x": {"callback_id": "cb_x", "hook_name": "init", "callback_repr": "func_x", "executed_count": 3},
            },
            "blindspot_callbacks": {},
        },
    })

    # Save snapshot
    snapshot_file = os.path.join(tempfile.gettempdir(), "test_snapshot.json")
    calc.state.save_snapshot(snapshot_file)

    print(f"  Saved snapshot to {snapshot_file}")

    # Load lai vao state moi
    calc2 = EnergyCalculator(config)
    calc2.state.load_snapshot(snapshot_file)

    print(f"  Loaded: registered={len(calc2.state.registered_callbacks)}, executed={len(calc2.state.executed_counts)}")

    assert len(calc2.state.registered_callbacks) == 1
    assert calc2.state.get_historical_count("cb_x") == 3

    # Cleanup
    os.remove(snapshot_file)

    print("  [OK] PASSED\n")
    return True


def test_max_energy_clamp():
    """Test energy khong vuot qua max_energy."""
    print("=" * 60)
    print("TEST 5: Max energy clamp")
    print("=" * 60)

    config = EnergyConfig(
        callback_first_seen=100,
        new_hook_bonus=100,
        max_energy=50,
    )
    calc = EnergyCalculator(config)

    result = calc.process_request({
        "request_id": "clamp_001",
        "hook_coverage": {
            "registered_callbacks": {
                "cb_z": {"callback_id": "cb_z", "hook_name": "huge_hook", "callback_repr": "func_z"},
            },
            "executed_callbacks": {
                "cb_z": {"callback_id": "cb_z", "hook_name": "huge_hook", "callback_repr": "func_z", "executed_count": 1},
            },
            "blindspot_callbacks": {},
        },
    })

    print(f"  Raw energy would be: {100 + 100} = 200")
    print(f"  Clamped score: {result.score}")

    assert result.score == 50, f"Expected clamped to 50, got {result.score}"

    print("  [OK] PASSED\n")
    return True


if __name__ == "__main__":
    print("\n>> Running energy.py tests...\n")

    tests = [
        test_basic_energy_calculation,
        test_blindspot_bonus,
        test_with_real_data,
        test_snapshot_roundtrip,
        test_max_energy_clamp,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            if test_fn():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [FAIL] FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)

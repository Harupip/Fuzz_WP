"""
Mini end-to-end demo cho energy.py.

Script nay mo phong mot fuzz loop rat nho:
- tao per-request JSON giong runtime that
- cho EnergyScheduler doc file moi trong requests dir
- in score/tier tung request
- verify ket qua bang expected values

Chay:
    python demo_energy.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "fuzzer-core" / "fuzzing"))

from energy import EnergyScheduler


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def base_callback(
    callback_id: str,
    hook_name: str,
    callback_repr: str,
    callback_type: str = "action",
    source: str = "add_action",
) -> dict:
    return {
        "callback_id": callback_id,
        "type": callback_type,
        "hook_name": hook_name,
        "callback_repr": callback_repr,
        "priority": 10,
        "accepted_args": 1,
        "registered_from": "demo_energy.py",
        "registered_at": utc_now(),
        "removed_at": None,
        "removed_from": None,
        "is_active": True,
        "status": "registered_only",
        "source": source,
    }


CALLBACKS = {
    "home_render": base_callback(
        "demo_cb_home_render",
        "template_redirect",
        "demo_render_homepage",
    ),
    "admin_export": base_callback(
        "demo_cb_admin_export",
        "demo_secret_admin_export",
        "demo_export_orders",
    ),
    "refund_flow": base_callback(
        "demo_cb_refund_flow",
        "demo_process_refund",
        "demo_refund_handler",
        callback_type="filter",
        source="add_filter",
    ),
    "invoice_send": base_callback(
        "demo_cb_invoice_send",
        "demo_send_invoice_email",
        "demo_send_invoice",
    ),
}


def build_request(
    request_id: str,
    endpoint: str,
    registered_names: list[str],
    executed_names: list[str],
) -> dict:
    registered_callbacks = {}
    executed_callbacks = {}

    for name in registered_names:
        info = dict(CALLBACKS[name])
        info.update(
            {
                "request_id": request_id,
                "endpoint": endpoint,
                "input_signature": f"sig_{request_id}",
                "status": "covered" if name in executed_names else "registered_only",
            }
        )
        registered_callbacks[info["callback_id"]] = info

    for name in executed_names:
        base = dict(CALLBACKS[name])
        base.update(
            {
                "request_id": request_id,
                "endpoint": endpoint,
                "input_signature": f"sig_{request_id}",
                "fired_hook": base["hook_name"],
                "executed_from": "demo_runtime",
                "executed_count": 1,
                "first_seen": utc_now(),
                "last_seen": utc_now(),
            }
        )
        executed_callbacks[base["callback_id"]] = base

    blindspot_callbacks = {
        cb_id: info
        for cb_id, info in registered_callbacks.items()
        if cb_id not in executed_callbacks
    }

    return {
        "request_id": request_id,
        "timestamp": utc_now(),
        "http_method": "GET",
        "http_target": "/demo",
        "endpoint": endpoint,
        "input_signature": f"sig_{request_id}",
        "request_params": {
            "query_params": {"demo": request_id},
            "body_params": {},
            "headers": {"User-Agent": "demo-energy-script"},
            "cookies": [],
        },
        "errors": [],
        "response": {
            "status_code": 200,
            "time_ms": 12.5,
        },
        "hook_coverage": {
            "registered_callbacks": registered_callbacks,
            "executed_callbacks": executed_callbacks,
            "blindspot_callbacks": blindspot_callbacks,
        },
        "hook_coverage_summary": {
            "registered_callbacks": len(registered_callbacks),
            "executed_callbacks": len(executed_callbacks),
            "blindspot_callbacks": len(blindspot_callbacks),
        },
    }


def write_request_file(requests_dir: Path, request_data: dict) -> Path:
    filepath = requests_dir / f"{request_data['request_id']}.json"
    with filepath.open("w", encoding="utf-8") as handle:
        json.dump(request_data, handle, indent=2, ensure_ascii=False)
    return filepath


def assert_result(result, expected: dict) -> None:
    actual = {
        "score": result.score,
        "dominant_tier": result.dominant_tier,
        "first_seen_count": result.first_seen_count,
        "rare_count": result.rare_count,
        "frequent_count": result.frequent_count,
        "blindspot_hits": result.blindspot_hits,
        "new_hooks_discovered": result.new_hooks_discovered,
    }
    for key, expected_value in expected.items():
        actual_value = actual[key]
        if actual_value != expected_value:
            raise AssertionError(f"{key}: expected {expected_value}, got {actual_value}")


def main() -> int:
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = REPO_ROOT / "output" / "demo_energy_runs" / run_id
    requests_dir = run_dir / "requests"
    snapshot_path = run_dir / "total_coverage.demo.json"
    requests_dir.mkdir(parents=True, exist_ok=True)

    scheduler = EnergyScheduler(
        requests_dir=str(requests_dir),
        snapshot_path=str(snapshot_path),
    )

    steps = [
        {
            "request": build_request(
                request_id="001_homepage",
                endpoint="GET:/",
                registered_names=["home_render", "admin_export", "refund_flow"],
                executed_names=["home_render"],
            ),
            "expected": {
                "score": 22,
                "dominant_tier": "first_seen",
                "first_seen_count": 1,
                "rare_count": 0,
                "frequent_count": 0,
                "blindspot_hits": 0,
                "new_hooks_discovered": 1,
            },
            "note": "first_seen + new_hook bonus",
        },
        {
            "request": build_request(
                request_id="002_admin_export",
                endpoint="GET:/?export=1",
                registered_names=["home_render", "admin_export", "refund_flow"],
                executed_names=["admin_export"],
            ),
            "expected": {
                "score": 20,
                "dominant_tier": "first_seen",
                "first_seen_count": 1,
                "rare_count": 0,
                "frequent_count": 0,
                "blindspot_hits": 1,
                "new_hooks_discovered": 0,
            },
            "note": "blindspot callback duoc trigger",
        },
        {
            "request": build_request(
                request_id="003_admin_export_repeat",
                endpoint="GET:/?export=1&retry=1",
                registered_names=["home_render", "admin_export", "refund_flow"],
                executed_names=["admin_export"],
            ),
            "expected": {
                "score": 5,
                "dominant_tier": "rare",
                "first_seen_count": 0,
                "rare_count": 1,
                "frequent_count": 0,
                "blindspot_hits": 0,
                "new_hooks_discovered": 0,
            },
            "note": "callback lap lai nen roi vao tier rare",
        },
        {
            "request": build_request(
                request_id="004_invoice_send",
                endpoint="POST:/checkout",
                registered_names=["home_render", "admin_export", "refund_flow", "invoice_send"],
                executed_names=["invoice_send"],
            ),
            "expected": {
                "score": 22,
                "dominant_tier": "first_seen",
                "first_seen_count": 1,
                "rare_count": 0,
                "frequent_count": 0,
                "blindspot_hits": 0,
                "new_hooks_discovered": 1,
            },
            "note": "callback moi tren hook moi",
        },
    ]

    print("=" * 72)
    print("ENERGY DEMO")
    print("=" * 72)
    print(f"Run dir     : {run_dir}")
    print(f"Requests dir: {requests_dir}")
    print(f"Snapshot    : {snapshot_path}")
    print()

    for index, step in enumerate(steps, start=1):
        request_data = step["request"]
        request_file = write_request_file(requests_dir, request_data)
        results = scheduler.process_new_requests()

        if len(results) != 1:
            raise RuntimeError(
                f"Expected exactly 1 new result after writing {request_file.name}, got {len(results)}"
            )

        request_id, result = results[0]
        assert_result(result, step["expected"])

        print(f"Step {index}: {request_id}")
        print(f"  File : {request_file.name}")
        print(f"  Note : {step['note']}")
        print(f"  Score: {result.score}")
        print(f"  Tier : {result.dominant_tier}")
        print(
            "  Mix  : "
            f"first_seen={result.first_seen_count}, "
            f"rare={result.rare_count}, "
            f"frequent={result.frequent_count}, "
            f"blindspot_hits={result.blindspot_hits}, "
            f"new_hooks={result.new_hooks_discovered}"
        )
        print()

    scheduler.save_state()
    snapshot = scheduler.state.snapshot()

    print("-" * 72)
    print("FINAL SNAPSHOT")
    print("-" * 72)
    print(json.dumps(snapshot["metadata"], indent=2, ensure_ascii=False))
    print()
    print("Blindspots con lai:")
    for blindspot_id in sorted(scheduler.state.blindspot_ids):
        info = scheduler.state.registered_callbacks[blindspot_id]
        print(f"  - {info['hook_name']} :: {info['callback_repr']}")

    print()
    print("Demo passed. EnergyScheduler dang xu ly dung luong request JSON demo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

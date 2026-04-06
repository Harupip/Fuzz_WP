"""
Live demo cho energy.py voi shop-demo that.

Script nay:
- gui HTTP requests that vao WordPress/shop-demo dang chay o localhost:8088
- doi UOPZ ghi per-request JSON that vao output/requests
- dua chinh cac file runtime do vao EnergyScheduler
- in executed callbacks, energy score, tier, va snapshot cuoi

Chay:
    python demo_energy_shop_real.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error, parse, request


REPO_ROOT = Path(__file__).resolve().parent
REQUESTS_DIR = REPO_ROOT / "output" / "requests"
RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
RUN_DIR = REPO_ROOT / "output" / "demo_energy_runs" / f"shop_demo_real_{RUN_ID}"
SNAPSHOT_PATH = RUN_DIR / "total_coverage.shop_demo_real.json"
BASE_URL = "http://localhost:8088"

sys.path.insert(0, str(REPO_ROOT / "fuzzer-core" / "fuzzing"))

from energy import EnergyScheduler, read_request_file


def ensure_runtime_dirs() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    REQUESTS_DIR.mkdir(parents=True, exist_ok=True)


def current_request_files() -> set[str]:
    return {path.name for path in REQUESTS_DIR.glob("*.json")}


def decode_response_body(raw: bytes) -> tuple[str, Any]:
    text = raw.decode("utf-8", errors="replace")
    trimmed = text
    if "<!DOCTYPE html>" in trimmed:
        trimmed = trimmed.split("<!DOCTYPE html>", 1)[0].strip()

    if not trimmed:
        return text, None

    try:
        return text, json.loads(trimmed)
    except json.JSONDecodeError:
        return text, None


def send_http_request(method: str, url: str, form_data: dict[str, Any] | None = None) -> tuple[int, str, Any]:
    headers = {"User-Agent": "codex-energy-live-demo"}
    data = None

    if form_data is not None:
        encoded = parse.urlencode(form_data).encode("utf-8")
        data = encoded
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    req = request.Request(url, data=data, method=method, headers=headers)

    try:
        with request.urlopen(req, timeout=15) as response:
            body_text, json_payload = decode_response_body(response.read())
            return response.status, body_text, json_payload
    except error.HTTPError as exc:
        body_text, json_payload = decode_response_body(exc.read())
        return exc.code, body_text, json_payload


def wait_for_new_request_files(previous: set[str], timeout_seconds: float = 12.0) -> list[Path]:
    deadline = time.time() + timeout_seconds
    found: list[Path] = []

    while time.time() < deadline:
        current = current_request_files()
        new_names = sorted(current - previous)
        if new_names:
            # Cho PHP ghi file xong han roi moi doc.
            time.sleep(0.8)
            found = [REQUESTS_DIR / name for name in new_names]
            break
        time.sleep(0.25)

    if not found:
        raise RuntimeError("Khong thay request JSON moi trong output/requests sau khi gui request that")

    return found


def executed_callback_lines(request_data: dict) -> list[str]:
    executed = request_data.get("hook_coverage", {}).get("executed_callbacks", {})
    lines = []
    for info in executed.values():
        hook_name = info.get("hook_name", "unknown_hook")
        callback_repr = info.get("callback_repr", "unknown_callback")
        lines.append(f"{hook_name} :: {callback_repr}")
    return sorted(lines)


def process_live_request(
    scheduler: EnergyScheduler,
    label: str,
    method: str,
    url: str,
    form_data: dict[str, Any] | None = None,
) -> dict:
    before = current_request_files()
    status_code, body_text, json_payload = send_http_request(method, url, form_data=form_data)
    new_files = wait_for_new_request_files(before)

    processed = []
    for filepath in new_files:
        result = scheduler.process_request_file(str(filepath))
        if result is None:
            continue

        request_data = read_request_file(str(filepath)) or {}
        processed.append(
            {
                "file": filepath,
                "result": result,
                "request_data": request_data,
            }
        )

    if not processed:
        raise RuntimeError(f"Khong process duoc request file moi cho buoc: {label}")

    primary = processed[-1]
    request_data = primary["request_data"]
    result = primary["result"]

    return {
        "label": label,
        "status_code": status_code,
        "body_text": body_text,
        "json_payload": json_payload,
        "request_file": primary["file"],
        "request_id": request_data.get("request_id", primary["file"].stem),
        "result": result,
        "executed_callbacks": executed_callback_lines(request_data),
    }


def require_callback(step: dict, needle: str) -> None:
    joined = "\n".join(step["executed_callbacks"])
    if needle not in joined:
        raise AssertionError(f"Buoc '{step['label']}' khong trigger callback mong doi: {needle}")


def main() -> int:
    ensure_runtime_dirs()

    scheduler = EnergyScheduler(
        requests_dir=str(REQUESTS_DIR),
        snapshot_path=str(SNAPSHOT_PATH),
        snapshot_interval=999999,
    )

    print("=" * 76)
    print("LIVE ENERGY DEMO FOR SHOP-DEMO")
    print("=" * 76)
    print(f"Base URL    : {BASE_URL}")
    print(f"Requests dir: {REQUESTS_DIR}")
    print(f"Snapshot    : {SNAPSHOT_PATH}")
    print()

    steps = []

    ui_first = process_live_request(
        scheduler=scheduler,
        label="UI first hit",
        method="GET",
        url=f"{BASE_URL}/?test-shop=1&codex_energy_demo={RUN_ID}",
    )
    require_callback(ui_first, "template_redirect :: shop_render_test_ui")
    steps.append(ui_first)

    ui_repeat = process_live_request(
        scheduler=scheduler,
        label="UI repeat hit",
        method="GET",
        url=f"{BASE_URL}/?test-shop=1&codex_energy_demo={RUN_ID}&repeat=1",
    )
    require_callback(ui_repeat, "template_redirect :: shop_render_test_ui")
    if ui_repeat["result"].score >= ui_first["result"].score:
        raise AssertionError("Request lap lai dang khong giam energy nhu mong doi")
    steps.append(ui_repeat)

    list_products = process_live_request(
        scheduler=scheduler,
        label="GET products",
        method="GET",
        url=f"{BASE_URL}/index.php?rest_route=/shop/v1/products&demo_run={RUN_ID}",
    )
    require_callback(list_products, "rest_api_init :: shop_register_endpoints")
    steps.append(list_products)

    create_product = process_live_request(
        scheduler=scheduler,
        label="POST create product",
        method="POST",
        url=f"{BASE_URL}/index.php?rest_route=/shop/v1/products",
        form_data={
            "name": f"Codex Demo Product {RUN_ID}",
            "description": "Created by live energy demo",
            "price": "199.99",
            "stock": "7",
        },
    )
    require_callback(create_product, "shop_product_created :: Closure@shop-demo.php:58")
    steps.append(create_product)

    payload = create_product["json_payload"] or {}
    product_id = payload.get("inserted_id")
    if not product_id:
        raise AssertionError("Khong lay duoc inserted_id tu response create product")

    get_product = process_live_request(
        scheduler=scheduler,
        label="GET single product",
        method="GET",
        url=f"{BASE_URL}/index.php?rest_route=/shop/v1/products/{product_id}",
    )
    require_callback(get_product, "rest_api_init :: shop_register_endpoints")
    steps.append(get_product)

    if create_product["result"].score <= ui_repeat["result"].score:
        raise AssertionError("Create product dang co energy qua thap so voi request lap lai UI")

    scheduler.save_state()
    snapshot = scheduler.state.snapshot()

    for index, step in enumerate(steps, start=1):
        result = step["result"]
        print(f"Step {index}: {step['label']}")
        print(f"  HTTP        : {step['status_code']}")
        print(f"  Request ID  : {step['request_id']}")
        print(f"  Request file: {step['request_file'].name}")
        print(f"  Score/Tier  : {result.score} / {result.dominant_tier}")
        print(
            "  Mix         : "
            f"first_seen={result.first_seen_count}, "
            f"rare={result.rare_count}, "
            f"frequent={result.frequent_count}, "
            f"blindspot_hits={result.blindspot_hits}, "
            f"new_hooks={result.new_hooks_discovered}"
        )
        print("  Executed    :")
        for line in step["executed_callbacks"]:
            print(f"    - {line}")
        if step["json_payload"] is not None:
            print(f"  Response    : {json.dumps(step['json_payload'], ensure_ascii=False)}")
        else:
            preview = step["body_text"][:100].replace("\r", " ").replace("\n", " ")
            print(f"  Response    : {preview}...")
        print()

    print("-" * 76)
    print("FINAL SNAPSHOT")
    print("-" * 76)
    print(json.dumps(snapshot["metadata"], indent=2, ensure_ascii=False))
    print()
    print("Ghi chu runtime:")
    print("  - REST request that cua shop-demo co the di tiep vao phase render theme.")
    print("  - Vi vay mot so request REST co them callback nhu the_content/template_redirect.")
    print("  - Day la hanh vi that cua app hien tai, khong phai du lieu fake.")
    print()
    print("Blindspots con lai trong state demo:")
    for blindspot_id in sorted(scheduler.state.blindspot_ids):
        info = scheduler.state.registered_callbacks[blindspot_id]
        print(f"  - {info.get('hook_name')} :: {info.get('callback_repr')}")

    print()
    print("Live demo passed. Energy dang chay tren request JSON that cua shop-demo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

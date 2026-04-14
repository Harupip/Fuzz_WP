from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import parse

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from hook_energy_demo.seed_pipeline import HookSeedAnalyzer


def build_registered_callback(
    callback_id: str,
    hook_name: str,
    callback_repr: str,
    *,
    callback_type: str = "action",
    priority: int = 10,
    accepted_args: int = 1,
    is_active: bool = True,
    status: str = "registered_only",
) -> dict:
    return {
        "callback_id": callback_id,
        "hook_name": hook_name,
        "callback_repr": callback_repr,
        "type": callback_type,
        "priority": priority,
        "accepted_args": accepted_args,
        "source_file": "/var/www/html/wp-content/plugins/shop-demo/shop-demo.php",
        "source_line": 123,
        "is_active": is_active,
        "status": status,
    }


def build_executed_callback(
    callback_id: str,
    hook_name: str,
    callback_repr: str,
    *,
    callback_type: str = "action",
    priority: int = 10,
    executed_count: int = 1,
) -> dict:
    return {
        "callback_id": callback_id,
        "hook_name": hook_name,
        "callback_repr": callback_repr,
        "type": callback_type,
        "priority": priority,
        "executed_count": executed_count,
    }


def build_registry_hook(
    callback_id: str,
    hook_name: str,
    callback_repr: str,
    *,
    callback_type: str = "action",
    priority: int = 10,
    accepted_args: int = 1,
    executed_count: int = 0,
    fire_count: int = 0,
) -> dict:
    return {
        "hook_name": hook_name,
        "type": callback_type,
        "emitters": {
            "demo_emitter": {
                "fire_count": fire_count,
                "apis": ["do_action"],
            }
        }
        if fire_count
        else {},
        "callbacks": {
            callback_id: {
                "callback_id": callback_id,
                "callback_repr": callback_repr,
                "type": callback_type,
                "priority": priority,
                "accepted_args": accepted_args,
                "executed_count": executed_count,
            }
        },
    }


class HookSeedPipelineTests(unittest.TestCase):
    """
    Mục đích:
    - Kiểm thử riêng cho pipeline uncovered-callback extraction và seed generation.
    -
    Tham số:
    - Không có tham số đầu vào khi khai báo test case.
    -
    Giá trị trả về:
    - Không áp dụng vì đây là test class.
    -
    Logic chính:
    - Bao phủ callback comparison, seed generation, unsupported hook handling, và replay contract.
    -
    Vì sao cần class này trong pipeline seed generation:
    - Phần seed mới phải được kiểm tra tách biệt để đảm bảo không phụ thuộc vào logic energy cũ.
    """

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="hook-seed-pipeline-")
        self.coverage_file = Path(self.temp_dir.name) / "total_coverage.json"
        self.registry_file = Path(self.temp_dir.name) / "hook_registry.json"
        self.analyzer = HookSeedAnalyzer(str(self.coverage_file), str(self.registry_file))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_payloads(self, *, registered: dict, executed: dict, registry_hooks: dict) -> None:
        coverage_payload = {
            "metadata": {
                "total_registered_callbacks": len(registered),
                "total_executed_callbacks": len(executed),
            },
            "data": {
                "registered_callbacks": registered,
                "executed_callbacks": executed,
                "blindspot_callbacks": {
                    callback_id: item
                    for callback_id, item in registered.items()
                    if callback_id not in executed
                },
            },
        }
        registry_payload = {
            "hooks": registry_hooks,
        }
        self.coverage_file.write_text(json.dumps(coverage_payload, indent=2), encoding="utf-8")
        self.registry_file.write_text(json.dumps(registry_payload, indent=2), encoding="utf-8")

    def test_gap_extraction_handles_multiple_callbacks_under_same_hook(self) -> None:
        self.write_payloads(
            registered={
                "cb-uncovered": build_registered_callback("cb-uncovered", "wp_ajax_nopriv_load_more", "Demo::uncovered"),
                "cb-covered": build_registered_callback("cb-covered", "wp_ajax_nopriv_load_more", "Demo::covered"),
            },
            executed={
                "cb-covered": build_executed_callback("cb-covered", "wp_ajax_nopriv_load_more", "Demo::covered", executed_count=2),
            },
            registry_hooks={
                "wp_ajax_nopriv_load_more": {
                    "hook_name": "wp_ajax_nopriv_load_more",
                    "type": "action",
                    "emitters": {},
                    "callbacks": {
                        "cb-uncovered": {"executed_count": 0},
                        "cb-covered": {"executed_count": 2},
                    },
                }
            },
        )

        _, _, gap_entries, suggested_entries = self.analyzer.analyze()
        by_id = {item.callback_id: item for item in gap_entries}

        self.assertEqual(by_id["cb-uncovered"].status, "uncovered")
        self.assertEqual(by_id["cb-uncovered"].execute_count, 0)
        self.assertEqual(by_id["cb-covered"].status, "covered")
        self.assertEqual(by_id["cb-covered"].execute_count, 2)
        self.assertEqual([item.callback_id for item in suggested_entries], ["cb-uncovered"])

    def test_generates_seed_for_wp_ajax_hook(self) -> None:
        self.write_payloads(
            registered={
                "cb-ajax": build_registered_callback("cb-ajax", "wp_ajax_update_cart", "Shop_Demo_Ajax::update_cart"),
            },
            executed={},
            registry_hooks={
                "wp_ajax_update_cart": build_registry_hook("cb-ajax", "wp_ajax_update_cart", "Shop_Demo_Ajax::update_cart"),
            },
        )

        _, _, _, suggested_entries = self.analyzer.analyze()
        item = suggested_entries[0]
        self.assertEqual(item.seed_priority, "highest")
        self.assertTrue(item.direct_http_supported)
        self.assertEqual(item.seed.method, "POST")
        self.assertEqual(item.seed.path, "/wp-admin/admin-ajax.php")
        self.assertEqual(item.seed.body, {"action": "update_cart"})
        self.assertEqual(item.seed.auth_mode, "authenticated")

    def test_generates_seed_for_wp_ajax_nopriv_hook(self) -> None:
        self.write_payloads(
            registered={
                "cb-ajax-public": build_registered_callback("cb-ajax-public", "wp_ajax_nopriv_load_more", "Shop_Demo_Ajax::load_more"),
            },
            executed={},
            registry_hooks={
                "wp_ajax_nopriv_load_more": build_registry_hook("cb-ajax-public", "wp_ajax_nopriv_load_more", "Shop_Demo_Ajax::load_more"),
            },
        )

        _, _, _, suggested_entries = self.analyzer.analyze()
        item = suggested_entries[0]
        self.assertEqual(item.seed.path, "/wp-admin/admin-ajax.php")
        self.assertEqual(item.seed.body, {"action": "load_more"})
        self.assertEqual(item.seed.auth_mode, "unauth-capable")

    def test_generates_seed_for_admin_post_hook(self) -> None:
        self.write_payloads(
            registered={
                "cb-admin-post": build_registered_callback("cb-admin-post", "admin_post_export_orders", "Shop_Demo_Admin::export_orders"),
            },
            executed={},
            registry_hooks={
                "admin_post_export_orders": build_registry_hook("cb-admin-post", "admin_post_export_orders", "Shop_Demo_Admin::export_orders"),
            },
        )

        _, _, _, suggested_entries = self.analyzer.analyze()
        item = suggested_entries[0]
        self.assertEqual(item.seed.path, "/wp-admin/admin-post.php")
        self.assertEqual(item.seed.body, {"action": "export_orders"})
        self.assertEqual(item.seed.auth_mode, "authenticated")

    def test_internal_hook_does_not_get_fake_http_seed(self) -> None:
        self.write_payloads(
            registered={
                "cb-internal": build_registered_callback("cb-internal", "shop_process_refund", "Closure@shop-demo.php:308", callback_type="filter"),
            },
            executed={},
            registry_hooks={
                "shop_process_refund": build_registry_hook("cb-internal", "shop_process_refund", "Closure@shop-demo.php:308", callback_type="filter"),
            },
        )

        _, _, _, suggested_entries = self.analyzer.analyze()
        item = suggested_entries[0]
        self.assertFalse(item.direct_http_supported)
        self.assertIsNone(item.seed)
        self.assertEqual(item.generation_status, "manual_analysis_required")

    def test_replay_seed_can_verify_callback_becomes_covered(self) -> None:
        callback_id = "cb-replay"
        hook_name = "wp_ajax_nopriv_load_more"
        callback_repr = "Shop_Demo_Ajax::load_more"

        self.write_payloads(
            registered={
                callback_id: build_registered_callback(callback_id, hook_name, callback_repr),
            },
            executed={},
            registry_hooks={
                hook_name: build_registry_hook(callback_id, hook_name, callback_repr),
            },
        )

        coverage_file = self.coverage_file

        class ReplayHandler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                content_length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(content_length).decode("utf-8")
                params = parse.parse_qs(body)
                if self.path == "/wp-admin/admin-ajax.php" and params.get("action") == ["load_more"]:
                    payload = json.loads(coverage_file.read_text(encoding="utf-8"))
                    payload["data"]["executed_callbacks"][callback_id] = build_executed_callback(
                        callback_id,
                        hook_name,
                        callback_repr,
                        executed_count=1,
                    )
                    coverage_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"success":true}')
                    return

                self.send_response(404)
                self.end_headers()

            def log_message(self, format: str, *args) -> None:  # noqa: A003
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), ReplayHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = self.analyzer.replay_seed(
                f"http://127.0.0.1:{server.server_address[1]}",
                hook_name=hook_name,
                verify_after_replay=True,
                wait_seconds=1.0,
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertEqual(result["http_status"], 200)
        self.assertTrue(result["verification"]["covered_after_replay"])
        self.assertEqual(result["verification"]["execute_count_after_replay"], 1)


if __name__ == "__main__":
    unittest.main()

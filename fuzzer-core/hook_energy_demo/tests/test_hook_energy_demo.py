from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from hook_energy_demo.calculator import HookEnergyCalculator
from hook_energy_demo.collector import HookCollector
from hook_energy_demo.reporter import HookEnergyReporter
from hook_energy_demo.state import HookEnergyDemoState


def build_request_payload(
    request_id: str,
    executed_callbacks: dict[str, dict],
    registered_callbacks: dict[str, dict] | None = None,
    scenario_name: str = "",
) -> dict:
    """
    Mục đích:
    - Tạo payload request tối thiểu cho unit test của demo hook energy.
    -
    Tham số:
    - str request_id: ID request giả lập.
    - dict executed_callbacks: Callback thực thi trong request.
    - dict | None registered_callbacks: Callback đăng ký của request, nếu không truyền sẽ dùng dict rỗng.
    - str scenario_name: Tên scenario giả lập để test phần reporter.
    -
    Giá trị trả về:
    - dict: Payload đúng schema tối thiểu mà collector cần.
    -
    Logic chính:
    - Nhúng `scenario` vào body_params để collector suy ra tên request dễ đọc.
    -
    Tại sao cần hàm này trong demo hook energy:
    - Test cần dựng nhanh nhiều request khác nhau mà không phải lặp lại JSON boilerplate.
    """

    return {
        "request_id": request_id,
        "endpoint": f"REST:/demo/{request_id}",
        "request_params": {
            "body_params": {"scenario": scenario_name} if scenario_name else {},
            "headers": {},
        },
        "hook_coverage": {
            "registered_callbacks": registered_callbacks or {},
            "executed_callbacks": executed_callbacks,
        },
    }


class HookEnergyDemoTests(unittest.TestCase):
    """
    Mục đích:
    - Kiểm thử các quy tắc chính của standalone hook energy demo.
    -
    Tham số:
    - Không có tham số đầu vào khi khai báo test case.
    -
    Giá trị trả về:
    - Không áp dụng vì đây là test class.
    -
    Logic chính:
    - Bao phủ công thức score, aggregate `max`, trường hợp request rỗng, và snapshot state.
    -
    Tại sao cần class này trong demo hook energy:
    - Demo chỉ thuyết phục khi chứng minh được các ví dụ chấp nhận bằng test tự động.
    """

    def setUp(self) -> None:
        """
        Mục đích:
        - Khởi tạo collector/calculator/reporter sạch cho từng test.
        -
        Tham số:
        - Không có tham số đầu vào.
        -
        Giá trị trả về:
        - None.
        -
        Logic chính:
        - Mỗi test dùng state mới để tránh rò rỉ execution count giữa các case.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Các ví dụ về callback mới/hiếm chỉ đúng khi lịch sử execution được kiểm soát chặt.
        """

        self.collector = HookCollector(state=HookEnergyDemoState())
        self.calculator = HookEnergyCalculator()
        self.reporter = HookEnergyReporter()

    def test_new_callback_gets_score_one(self) -> None:
        """
        Mục đích:
        - Xác nhận callback chưa từng thực thi trước đó nhận score bằng 1.0.
        -
        Tham số:
        - Không có tham số đầu vào.
        -
        Giá trị trả về:
        - None.
        -
        Logic chính:
        - Tạo request với một callback mới, chấm điểm trước khi finalize state.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Đây là ví dụ cốt lõi chứng minh công thức 1 / (N + 1) được áp dụng đúng.
        """

        payload = build_request_payload(
            request_id="req-new",
            scenario_name="new-callback",
            registered_callbacks={
                "cb-new": {"hook_name": "shop_product_created", "callback_repr": "shop_demo_new", "priority": 10},
            },
            executed_callbacks={
                "cb-new": {"hook_name": "shop_product_created", "callback_repr": "shop_demo_new", "priority": 10, "executed_count": 1},
            },
        )

        observation = self.collector.collect_request(payload)
        report = self.calculator.calculate_request_energy(observation, self.collector)
        self.assertEqual(report.hook_energy, 1.0)
        self.assertEqual(report.executed_callbacks[0].score, 1.0)

    def test_old_callback_gets_smaller_score_after_finalize(self) -> None:
        """
        Mục đích:
        - Xác nhận callback đã chạy trước đó sẽ có score nhỏ hơn ở request sau.
        -
        Tham số:
        - Không có tham số đầu vào.
        -
        Giá trị trả về:
        - None.
        -
        Logic chính:
        - Chạy request đầu để tăng global count, rồi chấm request sau với cùng callback.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Demo phải cho thấy callback cũ mất dần ưu tiên khi đã quen thuộc hơn.
        """

        first_payload = build_request_payload(
            request_id="req-first",
            scenario_name="first-run",
            registered_callbacks={
                "cb-repeat": {"hook_name": "shop_before_update_product", "callback_repr": "shop_repeat", "priority": 10},
            },
            executed_callbacks={
                "cb-repeat": {"hook_name": "shop_before_update_product", "callback_repr": "shop_repeat", "priority": 10, "executed_count": 3},
            },
        )
        first_report = self.calculator.calculate_request_energy(self.collector.collect_request(first_payload), self.collector)
        self.collector.finalize_request(first_report)

        second_payload = build_request_payload(
            request_id="req-second",
            scenario_name="second-run",
            registered_callbacks={
                "cb-repeat": {"hook_name": "shop_before_update_product", "callback_repr": "shop_repeat", "priority": 10},
            },
            executed_callbacks={
                "cb-repeat": {"hook_name": "shop_before_update_product", "callback_repr": "shop_repeat", "priority": 10, "executed_count": 1},
            },
        )
        second_report = self.calculator.calculate_request_energy(self.collector.collect_request(second_payload), self.collector)

        self.assertEqual(second_report.executed_callbacks[0].previous_execution_count, 3)
        self.assertAlmostEqual(second_report.executed_callbacks[0].score, 0.25)
        self.assertAlmostEqual(second_report.hook_energy, 0.25)

    def test_request_energy_uses_max_score_among_unique_callbacks(self) -> None:
        """
        Mục đích:
        - Xác nhận request-level hook energy dùng `max`, không dùng tổng hay loop count.
        -
        Tham số:
        - Không có tham số đầu vào.
        -
        Giá trị trả về:
        - None.
        -
        Logic chính:
        - Seed state để một callback là phổ biến, callback còn lại là mới, rồi so sánh energy.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Đây là quy tắc aggregate chính được chọn để demo dễ debug và bounded trong [0, 1].
        """

        seed_payload = build_request_payload(
            request_id="req-seed",
            executed_callbacks={
                "cb-common": {"hook_name": "shop_order_placed", "callback_repr": "shop_common", "priority": 10, "executed_count": 4},
            },
        )
        seed_report = self.calculator.calculate_request_energy(self.collector.collect_request(seed_payload), self.collector)
        self.collector.finalize_request(seed_report)

        payload = build_request_payload(
            request_id="req-mixed",
            scenario_name="mixed-case",
            executed_callbacks={
                "cb-common": {"hook_name": "shop_order_placed", "callback_repr": "shop_common", "priority": 10, "executed_count": 5},
                "cb-rare": {"hook_name": "shop_demo_runtime_filter", "callback_repr": "shop_rare", "priority": 30, "executed_count": 1},
            },
        )
        report = self.calculator.calculate_request_energy(self.collector.collect_request(payload), self.collector)

        scores = {item.callback_id: item.score for item in report.executed_callbacks}
        self.assertAlmostEqual(scores["cb-common"], 0.2)
        self.assertAlmostEqual(scores["cb-rare"], 1.0)
        self.assertAlmostEqual(report.hook_energy, 1.0)
        self.assertAlmostEqual(report.hook_energy_avg, 0.6)

    def test_request_with_no_callbacks_returns_zero_energy(self) -> None:
        """
        Mục đích:
        - Xác nhận request không có callback tracked sẽ nhận energy bằng 0.
        -
        Tham số:
        - Không có tham số đầu vào.
        -
        Giá trị trả về:
        - None.
        -
        Logic chính:
        - Dùng payload rỗng ở phần `executed_callbacks` và kiểm tra output của calculator/reporter.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Demo phải an toàn cho request không chạm callback mà không bịa ra fallback score.
        """

        payload = build_request_payload(request_id="req-empty", scenario_name="empty-case", executed_callbacks={})
        report = self.calculator.calculate_request_energy(self.collector.collect_request(payload), self.collector)
        text = self.reporter.format_request_summary(report)

        self.assertEqual(report.hook_energy, 0.0)
        self.assertEqual(report.hook_energy_avg, 0.0)
        self.assertIn("Executed callbacks: none", text)

    def test_state_snapshot_roundtrip_preserves_execution_counts(self) -> None:
        """
        Mục đích:
        - Xác nhận state snapshot có thể lưu và nạp lại mà không mất execution count.
        -
        Tham số:
        - Không có tham số đầu vào.
        -
        Giá trị trả về:
        - None.
        -
        Logic chính:
        - Finalize một request, lưu snapshot ra file tạm, rồi load lại để so sánh.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Demo thường chạy nhiều phiên, nên state persistence phải đáng tin cậy.
        """

        payload = build_request_payload(
            request_id="req-save",
            scenario_name="save-case",
            registered_callbacks={
                "cb-save": {"hook_name": "shop_filter_products_list", "callback_repr": "shop_save", "priority": 10, "is_active": False, "status": "removed"},
            },
            executed_callbacks={
                "cb-save": {"hook_name": "shop_filter_products_list", "callback_repr": "shop_save", "priority": 10, "executed_count": 2},
            },
        )
        report = self.calculator.calculate_request_energy(self.collector.collect_request(payload), self.collector)
        self.collector.finalize_request(report)

        with tempfile.TemporaryDirectory(prefix="hook-energy-demo-") as temp_dir:
            snapshot_file = Path(temp_dir) / "state.json"
            self.collector.state.save(str(snapshot_file))
            restored = HookEnergyDemoState.load(str(snapshot_file))

        self.assertEqual(restored.callbacks["cb-save"].total_execution_count, 2)
        self.assertEqual(restored.callbacks["cb-save"].total_request_count, 1)
        self.assertFalse(restored.callbacks["cb-save"].is_active)


if __name__ == "__main__":
    unittest.main()

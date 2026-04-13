from __future__ import annotations

import json
from pathlib import Path

from .models import RequestEnergyReport
from .state import HookEnergyDemoState


class HookEnergyReporter:
    """
    Mục đích:
    - Tạo console output và JSON summary dễ đọc cho demo hook energy.
    -
    Tham số:
    - Không có tham số bắt buộc khi khởi tạo.
    -
    Giá trị trả về:
    - Không áp dụng vì đây là class reporter.
    -
    Logic chính:
    - Format từng request report, build ranking tổng hợp, và export report JSON.
    -
    Tại sao cần class này trong demo hook energy:
    - Mục tiêu của demo là làm tín hiệu energy "nhìn thấy được", nên reporter là phần
      biến dữ liệu thô thành câu chuyện rõ ràng cho người xem.
    """

    def format_request_summary(self, report: RequestEnergyReport) -> str:
        """
        Mục đích:
        - Tạo phần text tóm tắt cho một request theo style demo-friendly.
        -
        Tham số:
        - RequestEnergyReport report: Báo cáo energy của request cần in.
        -
        Giá trị trả về:
        - str: Chuỗi nhiều dòng mô tả callback đã chạy và energy cuối cùng.
        -
        Logic chính:
        - Nếu request không có callback tracked thì in energy 0;
          ngược lại liệt kê từng callback với N cũ, score, và số hit trong request.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Đây là phần trực quan nhất để chứng minh request nào "quan trọng" hơn.
        """

        lines = [
            f"Request: {report.scenario_name}",
            f"Request ID: {report.request_id}",
            f"Endpoint: {report.endpoint}",
        ]

        if not report.executed_callbacks:
            lines.append("Executed callbacks: none")
            lines.append("Final hook_energy = 0.000000")
            lines.append("Final hook_energy_avg = 0.000000")
            return "\n".join(lines)

        lines.append("Executed callbacks:")
        for item in report.executed_callbacks:
            lines.append(
                " - "
                f"{item.hook_name} :: {item.callback_identity} :: priority={item.priority} "
                f"=> N={item.previous_execution_count} "
                f"=> score={item.score:.6f} "
                f"=> request_hits={item.request_execution_count}"
            )

        lines.append(f"Final hook_energy = {report.hook_energy:.6f}")
        lines.append(f"Final hook_energy_avg = {report.hook_energy_avg:.6f}")
        return "\n".join(lines)

    def build_rankings(self, reports: list[RequestEnergyReport], state: HookEnergyDemoState) -> dict:
        """
        Mục đích:
        - Tạo các bảng xếp hạng tổng hợp để chứng minh hiệu ứng của hook energy.
        -
        Tham số:
        - list[RequestEnergyReport] reports: Các request đã được xử lý trong lần chạy này.
        - HookEnergyDemoState state: State toàn cục sau khi đã finalize các request.
        -
        Giá trị trả về:
        - dict: Dữ liệu ranking gồm top requests, rare callbacks, frequent callbacks, và never-executed callbacks.
        -
        Logic chính:
        - Sort request theo `hook_energy`, sort callback theo bộ đếm toàn cục, rồi cắt top 10.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Ranking giúp trình bày nhanh request/callback nào đáng chú ý nhất trong demo.
        """

        top_requests = sorted(
            reports,
            key=lambda item: (-item.hook_energy, -item.hook_energy_avg, item.request_id),
        )[:10]

        callback_items = list(state.callbacks.values())
        rare_callbacks = sorted(
            [item for item in callback_items if item.total_execution_count > 0],
            key=lambda item: (item.total_execution_count, item.total_request_count, item.callback_id),
        )[:10]
        frequent_callbacks = sorted(
            callback_items,
            key=lambda item: (-item.total_execution_count, -item.total_request_count, item.callback_id),
        )[:10]
        never_executed_callbacks = sorted(
            [item for item in callback_items if item.total_execution_count == 0],
            key=lambda item: (item.hook_name, item.priority, item.callback_identity),
        )[:10]

        return {
            "top_requests_by_hook_energy": [
                {
                    "request_id": item.request_id,
                    "scenario_name": item.scenario_name,
                    "endpoint": item.endpoint,
                    "hook_energy": item.hook_energy,
                    "hook_energy_avg": item.hook_energy_avg,
                }
                for item in top_requests
            ],
            "top_rare_callbacks": [
                {
                    **item.to_dict(),
                    "next_score_if_seen_again": 1.0 / float(item.total_execution_count + 1),
                }
                for item in rare_callbacks
            ],
            "top_frequent_callbacks": [
                {
                    **item.to_dict(),
                    "next_score_if_seen_again": 1.0 / float(item.total_execution_count + 1),
                }
                for item in frequent_callbacks
            ],
            "callbacks_never_executed_yet": [item.to_dict() for item in never_executed_callbacks],
        }

    def format_rankings(self, rankings: dict) -> str:
        """
        Mục đích:
        - Chuyển dữ liệu ranking thành text ngắn gọn để in cuối phiên demo.
        -
        Tham số:
        - dict rankings: Dữ liệu ranking đã được `build_rankings` tạo ra.
        -
        Giá trị trả về:
        - str: Chuỗi nhiều dòng mô tả các bảng xếp hạng chính.
        -
        Logic chính:
        - In từng section theo thứ tự ưu tiên: request quan trọng, callback hiếm, callback chưa từng chạy.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Người xem thường cần một tổng kết nhanh sau khi xem log từng request riêng lẻ.
        """

        lines = ["== Hook Energy Rankings =="]

        lines.append("Top requests by hook_energy:")
        for item in rankings.get("top_requests_by_hook_energy", []):
            lines.append(
                " - "
                f"{item['scenario_name']} ({item['request_id']}) => hook_energy={item['hook_energy']:.6f} "
                f"| hook_energy_avg={item['hook_energy_avg']:.6f}"
            )

        lines.append("Top rare callbacks:")
        for item in rankings.get("top_rare_callbacks", []):
            lines.append(
                " - "
                f"{item['hook_name']} :: {item['callback_identity']} :: priority={item['priority']} "
                f"=> total_execution_count={item['total_execution_count']} "
                f"| next_score={item['next_score_if_seen_again']:.6f}"
            )

        lines.append("Callbacks never executed yet:")
        for item in rankings.get("callbacks_never_executed_yet", []):
            lines.append(
                " - "
                f"{item['hook_name']} :: {item['callback_identity']} :: priority={item['priority']} "
                f"=> status={item['status']}"
            )

        return "\n".join(lines)

    def write_summary(self, filepath: str, reports: list[RequestEnergyReport], state: HookEnergyDemoState) -> None:
        """
        Mục đích:
        - Ghi summary JSON tổng hợp của lần chạy demo ra đĩa.
        -
        Tham số:
        - str filepath: Đường dẫn file JSON cần ghi.
        - list[RequestEnergyReport] reports: Danh sách request report của lần chạy hiện tại.
        - HookEnergyDemoState state: State toàn cục sau khi xử lý xong.
        -
        Giá trị trả về:
        - None.
        -
        Logic chính:
        - Ghi thông tin request, callback registry, và rankings vào cùng một artifact JSON.
        -
        Tại sao cần hàm này trong demo hook energy:
        - File summary giúp lưu lại bằng chứng cho buổi demo mà không cần đọc lại console log.
        """

        payload = {
            "schema_version": "hook-energy-demo-summary-v1",
            "requests_processed_in_run": [item.to_dict() for item in reports],
            "callback_registry": {callback_id: item.to_dict() for callback_id, item in sorted(state.callbacks.items())},
            "rankings": self.build_rankings(reports, state),
        }

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

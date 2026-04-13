from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from hook_energy_demo.calculator import HookEnergyCalculator
    from hook_energy_demo.collector import HookCollector
    from hook_energy_demo.reporter import HookEnergyReporter
    from hook_energy_demo.state import HookEnergyDemoState
else:
    from .calculator import HookEnergyCalculator
    from .collector import HookCollector
    from .reporter import HookEnergyReporter
    from .state import HookEnergyDemoState


def build_argument_parser() -> argparse.ArgumentParser:
    """
    Mục đích:
    - Tạo parser cho CLI demo hook energy.
    -
    Tham số:
    - Không có tham số đầu vào.
    -
    Giá trị trả về:
    - argparse.ArgumentParser: Parser đã khai báo các option cần thiết cho demo.
    -
    Logic chính:
    - Cung cấp mode one-shot mặc định và mode watch tùy chọn để bám theo request mới.
    -
    Tại sao cần hàm này trong demo hook energy:
    - Demo cần dễ chạy bằng một lệnh đơn giản nhưng vẫn có chỗ mở rộng để watch lâu dài.
    """

    repo_root = Path(__file__).resolve().parents[2]
    output_dir = repo_root / "output"

    parser = argparse.ArgumentParser(description="Standalone hook energy demo for shop-demo request artifacts.")
    parser.add_argument("--requests-dir", default=str(output_dir / "requests"), help="Directory containing request JSON artifacts.")
    parser.add_argument("--state-file", default=str(output_dir / "hook_energy_demo_state.json"), help="Snapshot file for global callback execution counts.")
    parser.add_argument("--summary-file", default=str(output_dir / "hook_energy_demo_summary.json"), help="Summary JSON output for the current run.")
    parser.add_argument("--limit", type=int, default=0, help="Process at most N pending request files in one pass. 0 means no limit.")
    parser.add_argument("--watch", action="store_true", help="Continuously watch the requests directory for new files.")
    parser.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds when --watch is enabled.")
    return parser


def process_pending_requests(
    collector: HookCollector,
    calculator: HookEnergyCalculator,
    reporter: HookEnergyReporter,
    requests_dir: str,
    limit: int = 0,
) -> list:
    """
    Mục đích:
    - Xử lý các request artifact chưa được tính energy trong thư mục output.
    -
    Tham số:
    - HookCollector collector: Collector giữ state và đọc artifact.
    - HookEnergyCalculator calculator: Calculator áp dụng công thức demo.
    - HookEnergyReporter reporter: Reporter dùng để in log request.
    - str requests_dir: Thư mục chứa file request JSON.
    - int limit: Giới hạn số request cần xử lý trong một lượt; 0 nghĩa là không giới hạn.
    -
    Giá trị trả về:
    - list: Danh sách `RequestEnergyReport` đã xử lý trong lượt này.
    -
    Logic chính:
    - Lấy danh sách pending file, đọc từng file, calculate energy, in summary,
      rồi mới finalize request để cập nhật global count.
    -
    Tại sao cần hàm này trong demo hook energy:
    - Đây là vòng điều phối tối thiểu nhưng đủ rõ ràng để chứng minh collector/calculator/reporter hoạt động tách biệt.
    """

    reports = []
    pending_files = collector.list_pending_request_files(requests_dir)
    if limit > 0:
        pending_files = pending_files[:limit]

    for filepath in pending_files:
        payload = collector.read_request_file(filepath)
        if payload is None:
            continue

        observation = collector.collect_request(payload, request_file=filepath)
        report = calculator.calculate_request_energy(observation, collector)
        print(reporter.format_request_summary(report))
        print("-" * 60)
        collector.finalize_request(report)
        reports.append(report)

    return reports


def main() -> int:
    """
    Mục đích:
    - Chạy CLI standalone cho demo hook-based energy.
    -
    Tham số:
    - Không có tham số trực tiếp; hàm đọc argument từ command line.
    -
    Giá trị trả về:
    - int: Mã thoát của chương trình, 0 khi chạy thành công.
    -
    Logic chính:
    - Load state cũ, xử lý request pending, lưu state/summary, và nếu cần thì watch thư mục requests.
    -
    Tại sao cần hàm này trong demo hook energy:
    - Đây là điểm vào đơn giản nhất để người dùng chạy demo mà không cần tích hợp vào PHUZZ.
    """

    parser = build_argument_parser()
    args = parser.parse_args()

    state = HookEnergyDemoState.load(args.state_file)
    collector = HookCollector(state=state)
    calculator = HookEnergyCalculator()
    reporter = HookEnergyReporter()
    reports: list = []

    def _flush_outputs() -> None:
        """
        Mục đích:
        - Lưu state và summary sau mỗi lượt xử lý để tránh mất dữ liệu khi dừng đột ngột.
        -
        Tham số:
        - Không có tham số đầu vào.
        -
        Giá trị trả về:
        - None.
        -
        Logic chính:
        - Ghi state snapshot trước, sau đó ghi summary của lượt chạy hiện tại.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Demo thường được chạy thủ công; việc lưu liên tục giúp kết quả luôn sẵn để trình bày.
        """

        collector.state.save(args.state_file)
        reporter.write_summary(args.summary_file, reports, collector.state)

    reports.extend(process_pending_requests(collector, calculator, reporter, args.requests_dir, args.limit))
    if reports:
        print(reporter.format_rankings(reporter.build_rankings(reports, collector.state)))
        _flush_outputs()
    elif not args.watch:
        print("No pending request artifacts found. State remains unchanged.")
        _flush_outputs()

    if not args.watch:
        return 0

    print(f"Watching {args.requests_dir} for new request artifacts...")
    try:
        while True:
            new_reports = process_pending_requests(collector, calculator, reporter, args.requests_dir, args.limit)
            if new_reports:
                reports.extend(new_reports)
                print(reporter.format_rankings(reporter.build_rankings(reports, collector.state)))
                _flush_outputs()
            time.sleep(max(0.1, float(args.interval)))
    except KeyboardInterrupt:
        _flush_outputs()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

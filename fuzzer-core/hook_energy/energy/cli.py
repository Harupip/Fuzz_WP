from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from hook_energy.energy.calculator import HookEnergyCalculator
    from hook_energy.energy.collector import HookCollector
    from hook_energy.energy.reporter import HookEnergyReporter
    from hook_energy.energy.state import HookEnergyDemoState
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

    # CLI lives under fuzzer-core/hook_energy/energy, but runtime artifacts live in the repo-root output/.
    repo_root = Path(__file__).resolve().parents[3]
    output_dir = repo_root / "output"

    parser = argparse.ArgumentParser(description="Standalone hook energy demo for shop-demo request artifacts.")
    parser.add_argument("--requests-dir", default=str(output_dir / "requests"), help="Directory containing request JSON artifacts.")
    parser.add_argument("--state-file", default=str(output_dir / "hook_energy_state.json"), help="Snapshot file for global callback execution counts.")
    parser.add_argument("--summary-file", default=str(output_dir / "hook_energy_summary.json"), help="Summary JSON output for the current run.")
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


def requests_dir_has_artifacts(requests_dir: str) -> bool:
    """
    Mục đích:
    - Kiểm tra thư mục request hiện tại còn artifact JSON nào hay không.
    -
    Tham số:
    - str requests_dir: Thư mục output/requests cần kiểm tra.
    -
    Giá trị trả về:
    - bool: True nếu còn ít nhất một file JSON request, ngược lại là False.
    -
    Logic chính:
    - Dùng tín hiệu "còn artifact hay không" để phân biệt giữa một phiên cũ
      và một phiên mới vừa được reset output.
    -
    Tại sao cần hàm này trong demo hook energy:
    - Nếu output/requests đã bị xóa sạch thì CLI nên coi đó là phiên mới,
      không nên load lại bảng cũ từ state snapshot trước đó.
    """

    base = Path(requests_dir)
    return base.exists() and any(base.glob("*.json"))


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

    has_request_artifacts = requests_dir_has_artifacts(args.requests_dir)
    state = HookEnergyDemoState.load(args.state_file) if has_request_artifacts else HookEnergyDemoState()
    collector = HookCollector(state=state)
    calculator = HookEnergyCalculator()
    reporter = HookEnergyReporter()
    reports: list = []
    last_dashboard_signature = None

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

    def _dashboard_signature() -> tuple:
        callback_items = tuple(
            sorted(
                (
                    callback_id,
                    item.hook_name,
                    item.callback_identity,
                    item.priority,
                    item.status,
                    item.total_execution_count,
                    item.total_request_count,
                )
                for callback_id, item in collector.state.callbacks.items()
            )
        )
        return (
            len(reports),
            len(collector.state.processed_request_ids),
            callback_items,
        )

    def _render_watch_dashboard(force: bool = False) -> None:
        nonlocal last_dashboard_signature

        signature = _dashboard_signature()
        if not force and signature == last_dashboard_signature:
            return

        last_dashboard_signature = signature
        rankings = reporter.build_rankings(reports, collector.state)

        if sys.stdout.isatty():
            print("\033[2J\033[H", end="")

        print(f"Watching {args.requests_dir} for new request artifacts...")
        print(
            "Live summary: "
            f"requests_processed={len(collector.state.processed_request_ids)} "
            f"| callbacks_tracked={len(collector.state.callbacks)} "
            f"| last_refresh={time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print()
        print(reporter.format_rankings(rankings))

    reports.extend(process_pending_requests(collector, calculator, reporter, args.requests_dir, args.limit))
    if reports:
        if not args.watch:
            print(reporter.format_rankings(reporter.build_rankings(reports, collector.state)))
        _flush_outputs()
    elif not has_request_artifacts:
        print("No request artifacts found. Starting a fresh session with empty state.")
        _flush_outputs()
    elif not args.watch:
        print("No pending request artifacts found. State remains unchanged.")
        _flush_outputs()

    if not args.watch:
        return 0

    _render_watch_dashboard(force=True)
    try:
        while True:
            new_reports = process_pending_requests(collector, calculator, reporter, args.requests_dir, args.limit)
            if new_reports:
                reports.extend(new_reports)
                _flush_outputs()
            _render_watch_dashboard()
            time.sleep(max(0.1, float(args.interval)))
    except KeyboardInterrupt:
        _flush_outputs()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from hook_energy.seed.pipeline import HookSeedAnalyzer
else:
    from .pipeline import HookSeedAnalyzer


def build_argument_parser() -> argparse.ArgumentParser:
    """
    Mục đích:
    - Tạo CLI cho pipeline seed generation của demo hook coverage.
    -
    Tham số:
    - Không có tham số đầu vào.
    -
    Giá trị trả về:
    - argparse.ArgumentParser: Parser chứa các option để generate và replay seed.
    -
    Logic chính:
    - Tách chế độ generate artifact và replay seed để người dùng demo từng bước rõ ràng.
    -
    Vì sao cần nó trong pipeline seed generation:
    - Demo seed cần lệnh riêng, độc lập với CLI energy hiện có để tránh đụng logic energy.
    """

    # CLI lives under fuzzer-core/hook_energy/seed, but runtime artifacts live in the repo-root output/.
    repo_root = Path(__file__).resolve().parents[3]
    output_dir = repo_root / "output"

    parser = argparse.ArgumentParser(description="Seed generation pipeline for uncovered WordPress callbacks.")
    parser.add_argument("--coverage-file", default=str(output_dir / "total_coverage.json"), help="Aggregate coverage JSON exported by the PHP runtime.")
    parser.add_argument("--registry-file", default=str(output_dir / "hook_registry.json"), help="Aggregate hook registry JSON exported by the PHP runtime.")
    parser.add_argument("--gap-output", default=str(output_dir / "hook_gap_report.json"), help="Machine-readable uncovered callback report.")
    parser.add_argument("--seed-output", default=str(output_dir / "suggested_seeds.json"), help="Machine-readable suggested seed output.")
    parser.add_argument("--seed-markdown-output", default=str(output_dir / "suggested_seeds.md"), help="Human-readable seed output.")
    parser.add_argument("--target-base-url", default="http://127.0.0.1:8088", help="Base URL used when replaying a generated seed.")
    parser.add_argument("--replay-hook", default="", help="Replay the generated seed for this hook name after generating outputs.")
    parser.add_argument("--replay-callback-id", default="", help="Replay the generated seed for this callback id after generating outputs.")
    parser.add_argument("--verify-after-replay", action="store_true", help="Poll aggregate coverage after replay to verify the callback becomes covered.")
    parser.add_argument("--wait-seconds", type=float, default=2.0, help="How long to wait for aggregate coverage to update after replay.")
    return parser


def main() -> int:
    """
    Mục đích:
    - Chạy pipeline seed generation end-to-end cho demo hiện tại.
    -
    Tham số:
    - Không có tham số trực tiếp; hàm đọc từ command line.
    -
    Giá trị trả về:
    - int: Mã thoát của chương trình.
    -
    Logic chính:
    - Generate gap report, generate seed outputs, rồi optional replay một seed để kiểm chứng.
    -
    Vì sao cần nó trong pipeline seed generation:
    - Đây là entry point tối thiểu để người dùng tạo artifact và kiểm chứng uncovered -> covered.
    """

    args = build_argument_parser().parse_args()
    analyzer = HookSeedAnalyzer(args.coverage_file, args.registry_file)
    coverage_payload, _, gap_entries, suggested_entries = analyzer.analyze()

    gap_report = analyzer.build_gap_report(coverage_payload, gap_entries)
    seed_report = analyzer.build_seed_report(suggested_entries)
    analyzer.write_json(args.gap_output, gap_report)
    analyzer.write_json(args.seed_output, seed_report)
    analyzer.write_seed_markdown(args.seed_markdown_output, suggested_entries)

    print(
        "Seed pipeline summary: "
        f"registered={gap_report['summary']['registered_callbacks']} "
        f"| uncovered={gap_report['summary']['uncovered_callbacks']} "
        f"| direct_http_candidates={gap_report['summary']['direct_http_seed_candidates']}"
    )

    replay_hook = args.replay_hook.strip()
    replay_callback_id = args.replay_callback_id.strip()
    if replay_hook or replay_callback_id:
        replay_result = analyzer.replay_seed(
            args.target_base_url,
            hook_name=replay_hook or None,
            callback_id=replay_callback_id or None,
            verify_after_replay=args.verify_after_replay,
            wait_seconds=args.wait_seconds,
        )
        print(json.dumps(replay_result, indent=2, ensure_ascii=False))

        refreshed_coverage, _, refreshed_gaps, refreshed_suggestions = analyzer.analyze()
        analyzer.write_json(args.gap_output, analyzer.build_gap_report(refreshed_coverage, refreshed_gaps))
        analyzer.write_json(args.seed_output, analyzer.build_seed_report(refreshed_suggestions))
        analyzer.write_seed_markdown(args.seed_markdown_output, refreshed_suggestions)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

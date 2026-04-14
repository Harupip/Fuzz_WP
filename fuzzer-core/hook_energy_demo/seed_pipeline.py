from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from .seed_models import CallbackGap, SeedRequestTemplate


class HookSeedAnalyzer:
    """
    Mục đích:
    - Phân tích dữ liệu runtime hiện có để tìm uncovered callbacks và sinh seed tối thiểu.
    -
    Tham số:
    - coverage_file, registry_file trỏ tới các artifact aggregate đã có sẵn của demo.
    -
    Giá trị trả về:
    - Không áp dụng vì đây là class điều phối phân tích.
    -
    Logic chính:
    - Đọc aggregate coverage, đối chiếu callback đã đăng ký với callback đã thực thi,
      sau đó xếp hạng và suy ra seed HTTP khi hook có thể ánh xạ trực tiếp.
    -
    Vì sao cần nó trong pipeline seed generation:
    - Đây là lớp riêng cho seed generation để không trộn mục tiêu "tìm seed" với logic energy hiện có.
    """

    def __init__(self, coverage_file: str, registry_file: str) -> None:
        self.coverage_file = Path(coverage_file)
        self.registry_file = Path(registry_file)

    def load_json(self, filepath: Path) -> dict[str, Any]:
        """
        Mục đích:
        - Đọc một file JSON aggregate của demo một cách an toàn.
        -
        Tham số:
        - Path filepath: Đường dẫn file cần đọc.
        -
        Giá trị trả về:
        - dict[str, Any]: Nội dung JSON; nếu file chưa có thì trả dict rỗng.
        -
        Logic chính:
        - Không ném exception ra ngoài để CLI seed có thể báo trạng thái rõ ràng hơn.
        -
        Vì sao cần nó trong pipeline seed generation:
        - Seed pipeline phải tái sử dụng artifact hiện có mà không làm vỡ flow demo nếu file chưa sẵn sàng.
        """

        if not filepath.exists():
            return {}

        try:
            return json.loads(filepath.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def analyze(self) -> tuple[dict[str, Any], dict[str, Any], list[CallbackGap], list[CallbackGap]]:
        """
        Mục đích:
        - Chạy toàn bộ pipeline phân tích seed trên aggregate coverage hiện có.
        -
        Tham số:
        - Không có tham số đầu vào ngoài file đã cấu hình trong object.
        -
        Giá trị trả về:
        - tuple: `(coverage_payload, registry_payload, gap_entries, suggested_entries)`.
        -
        Logic chính:
        - Đọc file nguồn, build gap entries, rồi lọc/sort ra danh sách candidate dùng cho seed.
        -
        Vì sao cần nó trong pipeline seed generation:
        - Đây là entry point nhỏ gọn để cả CLI, test, và replay dùng chung cùng một logic.
        """

        coverage_payload = self.load_json(self.coverage_file)
        registry_payload = self.load_json(self.registry_file)
        gap_entries = self.build_gap_entries(coverage_payload, registry_payload)
        suggested_entries = self.build_seed_suggestions(gap_entries)
        return coverage_payload, registry_payload, gap_entries, suggested_entries

    def build_gap_entries(self, coverage_payload: dict[str, Any], registry_payload: dict[str, Any]) -> list[CallbackGap]:
        """
        Mục đích:
        - Hàm này dùng để đối chiếu callback đã đăng ký và callback đã thực thi.
        -
        Tham số:
        - coverage_payload: Dữ liệu aggregate từ `total_coverage.json`.
        - registry_payload: Dữ liệu aggregate từ `hook_registry.json`.
        -
        Giá trị trả về:
        - list[CallbackGap]: Danh sách callback đã được chuẩn hóa với trạng thái covered/uncovered.
        -
        Logic chính:
        - Mục tiêu là tìm ra callback còn chưa được chạy để sinh seed phù hợp.
        - Nếu dữ liệu normalize chưa đủ chắc chắn thì giữ lại cả raw callback để debug.
        -
        Vì sao cần nó trong pipeline seed generation:
        - Đây là bước chuyển từ coverage raw sang danh sách gap callback-level mà seed generator có thể tiêu thụ.
        """

        coverage_data = coverage_payload.get("data", {})
        registered_callbacks = coverage_data.get("registered_callbacks", {})
        executed_callbacks = coverage_data.get("executed_callbacks", {})
        registry_hooks = registry_payload.get("hooks", {})

        gap_entries: list[CallbackGap] = []
        for callback_id in sorted(registered_callbacks):
            registered_entry = registered_callbacks.get(callback_id, {})
            hook_name = str(registered_entry.get("hook_name", "")).strip()
            registry_callback = (
                registry_hooks.get(hook_name, {})
                .get("callbacks", {})
                .get(callback_id, {})
            )
            executed_entry = executed_callbacks.get(callback_id, {})

            callback_name = self._normalize_callback_name(registered_entry, executed_entry)
            callback_raw = str(
                registered_entry.get("callback_repr")
                or executed_entry.get("callback_repr")
                or callback_id
            )
            execute_count = max(
                int(executed_entry.get("executed_count", 0) or 0),
                int(registry_callback.get("executed_count", 0) or 0),
            )
            is_active = bool(registered_entry.get("is_active", True))
            registration_status = str(registered_entry.get("status", "registered_only"))
            status = "covered" if execute_count > 0 else "uncovered"
            seed_priority, priority_rank, target_family = self.classify_seed_priority(hook_name, is_active)
            seed_template, generation_status, extra_notes = self.generate_seed_template(hook_name, is_active, status)

            notes = list(extra_notes)
            if not is_active:
                notes.append("Callback is currently inactive or removed, so it should not be replayed as a live seed target.")

            gap_entries.append(
                CallbackGap(
                    callback_id=callback_id,
                    hook_name=hook_name,
                    callback_name=callback_name,
                    callback_raw=callback_raw,
                    callback_type=str(registered_entry.get("type", registered_entry.get("callback_type", "unknown"))),
                    priority=int(registered_entry.get("priority", 10) or 10),
                    accepted_args=int(registered_entry.get("accepted_args", 1) or 1),
                    source_file=registered_entry.get("source_file"),
                    source_line=self._safe_int(registered_entry.get("source_line")),
                    is_active=is_active,
                    registration_status=registration_status,
                    register_count=1,
                    execute_count=execute_count,
                    status=status,
                    seed_priority=seed_priority,
                    priority_rank=priority_rank,
                    target_family=target_family,
                    direct_http_supported=seed_template is not None,
                    generation_status=generation_status,
                    notes=notes,
                    seed=seed_template,
                    hook_fire_count=self._sum_hook_fire_count(registry_hooks.get(hook_name, {})),
                )
            )

        gap_entries.sort(
            key=lambda item: (
                0 if item.status == "uncovered" else 1,
                0 if item.is_active else 1,
                -item.priority_rank,
                item.hook_name,
                item.callback_name,
                item.callback_id,
            )
        )
        return gap_entries

    def build_seed_suggestions(self, gap_entries: list[CallbackGap]) -> list[CallbackGap]:
        """
        Mục đích:
        - Lọc và sắp xếp danh sách callback uncovered để lấy candidate seed hữu ích nhất.
        -
        Tham số:
        - list[CallbackGap] gap_entries: Toàn bộ callback đã được phân tích.
        -
        Giá trị trả về:
        - list[CallbackGap]: Danh sách candidate dành cho seed generation.
        -
        Logic chính:
        - Chỉ lấy callback còn uncovered và còn active.
        - Đây là ưu tiên cho seed generation chứ không thay thế energy hiện có.
        - Phần này chỉ phục vụ giai đoạn demo và chuẩn bị cho PHUZZ sau này.
        -
        Vì sao cần nó trong pipeline seed generation:
        - Seed generator không nên đẩy cả callback đã covered hoặc đã removed vào danh sách gợi ý.
        """

        candidates = [
            item
            for item in gap_entries
            if item.status == "uncovered" and item.is_active
        ]
        candidates.sort(
            key=lambda item: (
                -item.priority_rank,
                item.hook_name,
                item.callback_name,
                item.callback_id,
            )
        )
        return candidates

    def classify_seed_priority(self, hook_name: str, is_active: bool) -> tuple[str, int, str]:
        """
        Mục đích:
        - Xác định mức ưu tiên seed cho một hook uncovered.
        -
        Tham số:
        - str hook_name: Tên hook WordPress.
        - bool is_active: Callback còn active hay đã bị remove.
        -
        Giá trị trả về:
        - tuple[str, int, str]: `(priority_label, priority_rank, target_family)`.
        -
        Logic chính:
        - Tại sao `wp_ajax_*` và `admin_post_*` được ưu tiên cao:
          vì chúng ánh xạ trực tiếp sang entry point HTTP chuẩn của WordPress.
        - Đây là ưu tiên cho seed generation chứ không thay thế energy hiện có.
        - Phần này chỉ phục vụ giai đoạn demo và chuẩn bị cho PHUZZ sau này.
        -
        Vì sao cần nó trong pipeline seed generation:
        - Demo cần xếp uncovered callbacks theo khả năng replay thực tế thay vì chỉ nhìn theo hook name chung chung.
        """

        if not is_active:
            return "inactive", 0, "inactive"

        if hook_name.startswith("wp_ajax_nopriv_"):
            return "highest", 400, "wp_ajax_nopriv"
        if hook_name.startswith("wp_ajax_"):
            return "highest", 390, "wp_ajax"
        if hook_name.startswith("admin_post_nopriv_"):
            return "highest", 380, "admin_post_nopriv"
        if hook_name.startswith("admin_post_"):
            return "highest", 370, "admin_post"

        lowered = hook_name.lower()
        if lowered in {"init", "plugins_loaded", "wp_loaded"}:
            return "low", 100, "lifecycle"

        request_tokens = ("ajax", "request", "submit", "endpoint", "api")
        if any(token in lowered for token in request_tokens):
            return "medium", 200, "request_oriented"

        return "low", 120, "internal_or_manual"

    def generate_seed_template(
        self,
        hook_name: str,
        is_active: bool,
        coverage_status: str,
    ) -> tuple[SeedRequestTemplate | None, str, list[str]]:
        """
        Mục đích:
        - Hàm này sinh seed HTTP tối thiểu từ tên hook WordPress.
        -
        Tham số:
        - hook_name: Hook cần suy seed.
        - is_active: Callback còn active hay không.
        - coverage_status: `covered` hoặc `uncovered`.
        -
        Giá trị trả về:
        - tuple: `(seed_template | None, generation_status, notes)`.
        -
        Logic chính:
        - Với `wp_ajax_*` thì action nằm ở phần hậu tố của hook name.
        - Seed ở đây chỉ là điểm bắt đầu để chạm vào callback, chưa phải payload fuzz hoàn chỉnh.
        - Nếu hook không ánh xạ trực tiếp ra HTTP entry point thì chỉ ghi chú chứ không bịa request.
        -
        Vì sao cần nó trong pipeline seed generation:
        - Đây là bước biến uncovered callback thành request seed có thể replay thủ công hoặc cắm sang PHUZZ sau này.
        """

        if not is_active:
            return None, "inactive_callback", ["Callback is inactive, so no replay seed should be generated."]

        if coverage_status != "uncovered":
            return None, "already_covered", ["Callback is already covered in aggregate runtime data."]

        if hook_name.startswith("wp_ajax_nopriv_"):
            action = hook_name.removeprefix("wp_ajax_nopriv_")
            return (
                SeedRequestTemplate(
                    method="POST",
                    path="/wp-admin/admin-ajax.php",
                    content_type="application/x-www-form-urlencoded",
                    body={"action": action},
                    auth_mode="unauth-capable",
                ),
                "supported_http_seed",
                ["Direct WordPress AJAX entry point derived from `wp_ajax_nopriv_*` hook name."],
            )

        if hook_name.startswith("wp_ajax_"):
            action = hook_name.removeprefix("wp_ajax_")
            return (
                SeedRequestTemplate(
                    method="POST",
                    path="/wp-admin/admin-ajax.php",
                    content_type="application/x-www-form-urlencoded",
                    body={"action": action},
                    auth_mode="authenticated",
                ),
                "supported_http_seed",
                ["Direct WordPress AJAX entry point derived from `wp_ajax_*` hook name."],
            )

        if hook_name.startswith("admin_post_nopriv_"):
            action = hook_name.removeprefix("admin_post_nopriv_")
            return (
                SeedRequestTemplate(
                    method="POST",
                    path="/wp-admin/admin-post.php",
                    content_type="application/x-www-form-urlencoded",
                    body={"action": action},
                    auth_mode="unauth-capable",
                ),
                "supported_http_seed",
                ["Direct WordPress admin-post entry point derived from `admin_post_nopriv_*` hook name."],
            )

        if hook_name.startswith("admin_post_"):
            action = hook_name.removeprefix("admin_post_")
            return (
                SeedRequestTemplate(
                    method="POST",
                    path="/wp-admin/admin-post.php",
                    content_type="application/x-www-form-urlencoded",
                    body={"action": action},
                    auth_mode="authenticated",
                ),
                "supported_http_seed",
                ["Direct WordPress admin-post entry point derived from `admin_post_*` hook name."],
            )

        return None, "manual_analysis_required", [
            "This hook is uncovered, but a direct HTTP trigger path is not derivable from the hook name yet.",
            "Manual replay or later analysis is required.",
        ]

    def build_gap_report(self, coverage_payload: dict[str, Any], gap_entries: list[CallbackGap]) -> dict[str, Any]:
        uncovered_callbacks = [item for item in gap_entries if item.status == "uncovered"]
        direct_seed_candidates = [
            item for item in uncovered_callbacks if item.is_active and item.direct_http_supported
        ]

        return {
            "schema_version": "hook-gap-report-v1",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "source_files": {
                "coverage_file": str(self.coverage_file),
                "registry_file": str(self.registry_file),
            },
            "coverage_metadata": coverage_payload.get("metadata", {}),
            "summary": {
                "registered_callbacks": len(gap_entries),
                "uncovered_callbacks": len(uncovered_callbacks),
                "active_uncovered_callbacks": len([item for item in uncovered_callbacks if item.is_active]),
                "direct_http_seed_candidates": len(direct_seed_candidates),
            },
            "callbacks": [item.to_dict() for item in gap_entries],
        }

    def build_seed_report(self, suggested_entries: list[CallbackGap]) -> dict[str, Any]:
        return {
            "schema_version": "hook-seed-suggestions-v1",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "summary": {
                "suggested_entries": len(suggested_entries),
                "direct_http_seed_candidates": len([item for item in suggested_entries if item.direct_http_supported]),
                "manual_only_entries": len([item for item in suggested_entries if not item.direct_http_supported]),
            },
            "suggested_seeds": [item.to_dict() for item in suggested_entries],
        }

    def write_json(self, filepath: str, payload: dict[str, Any]) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def write_seed_markdown(self, filepath: str, suggested_entries: list[CallbackGap]) -> None:
        """
        Mục đích:
        - Tạo bản markdown dễ đọc cho reviewer/demo khi xem danh sách seed.
        -
        Tham số:
        - filepath: Đường dẫn file markdown đầu ra.
        - suggested_entries: Các uncovered callback đã được chọn cho seed generation.
        -
        Giá trị trả về:
        - None.
        -
        Logic chính:
        - In rõ hook, callback, priority, và seed hoặc ghi chú manual.
        -
        Vì sao cần nó trong pipeline seed generation:
        - Demo thường cần một bản human-readable bên cạnh JSON để kiểm tra nhanh trước khi replay.
        """

        lines = [
            "# Suggested Seeds",
            "",
            f"Generated from `{self.coverage_file}` and `{self.registry_file}`.",
            "",
        ]

        if not suggested_entries:
            lines.append("No uncovered active callbacks were found.")
        else:
            for item in suggested_entries:
                lines.append(f"## {item.hook_name}")
                lines.append(f"- Callback: `{item.callback_name}`")
                lines.append(f"- Priority: `{item.seed_priority}`")
                lines.append(f"- Status: `{item.status}`")
                lines.append(f"- Generation: `{item.generation_status}`")
                if item.seed is not None:
                    lines.append(f"- Method: `{item.seed.method}`")
                    lines.append(f"- Path: `{item.seed.path}`")
                    lines.append(f"- Auth: `{item.seed.auth_mode}`")
                    lines.append(f"- Body: `{json.dumps(item.seed.body, ensure_ascii=False)}`")
                for note in item.notes:
                    lines.append(f"- Note: {note}")
                lines.append("")

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    def replay_seed(
        self,
        base_url: str,
        *,
        hook_name: str | None = None,
        callback_id: str | None = None,
        verify_after_replay: bool = False,
        wait_seconds: float = 2.0,
    ) -> dict[str, Any]:
        """
        Mục đích:
        - Replay một seed đã sinh ra để chứng minh callback có thể chuyển từ uncovered sang covered.
        -
        Tham số:
        - base_url: Base URL của target WordPress demo.
        - hook_name hoặc callback_id: Chọn seed cần replay.
        - verify_after_replay: Có poll lại aggregate coverage để kiểm tra sau replay hay không.
        - wait_seconds: Thời gian tối đa chờ aggregate coverage cập nhật.
        -
        Giá trị trả về:
        - dict[str, Any]: Kết quả replay gồm HTTP status và verification state.
        -
        Logic chính:
        - Bước này dùng để chứng minh seed sinh ra có thực sự chạm được callback hay không.
        - Đây là bằng chứng cho phần demo trước khi gắn vào PHUZZ.
        -
        Vì sao cần nó trong pipeline seed generation:
        - Không có replay thì seed chỉ là gợi ý tĩnh, chưa chứng minh được giá trị thực tế.
        """

        _, _, _, suggested_entries = self.analyze()
        target = self._select_replay_target(suggested_entries, hook_name=hook_name, callback_id=callback_id)
        if target is None:
            raise ValueError("Could not find a matching uncovered seed target to replay.")
        if target.seed is None:
            raise ValueError("Selected target does not have a direct HTTP seed to replay.")

        request_url = base_url.rstrip("/") + target.seed.path
        request_body = parse.urlencode(target.seed.body).encode("utf-8")
        replay_id = f"seed-replay-{target.callback_id[:12]}"
        req = request.Request(request_url, data=request_body, method=target.seed.method)
        req.add_header("Accept", "application/json")
        req.add_header("Content-Type", target.seed.content_type)
        req.add_header("User-Agent", "Codex-HookSeed-Replay/1.0")
        req.add_header("X-Uopz-Fuzz-Id", replay_id)

        status_code = 0
        response_preview = ""
        try:
            with request.urlopen(req, timeout=5) as response:
                status_code = int(response.status)
                response_preview = response.read(400).decode("utf-8", errors="replace")
        except error.HTTPError as exc:
            status_code = int(exc.code)
            response_preview = exc.read(400).decode("utf-8", errors="replace")

        verification: dict[str, Any] = {
            "covered_after_replay": False,
            "execute_count_after_replay": 0,
        }
        if verify_after_replay:
            verification = self._verify_callback_covered(target.callback_id, wait_seconds)

        return {
            "hook_name": target.hook_name,
            "callback_id": target.callback_id,
            "request": target.seed.to_dict(),
            "http_status": status_code,
            "response_preview": response_preview,
            "verification": verification,
        }

    def _normalize_callback_name(self, registered_entry: dict[str, Any], executed_entry: dict[str, Any]) -> str:
        for key in ("callback_repr", "stable_id", "runtime_id"):
            value = str(registered_entry.get(key) or executed_entry.get(key) or "").strip()
            if value:
                return value
        return str(registered_entry.get("callback_id") or executed_entry.get("callback_id") or "unknown_callback")

    def _sum_hook_fire_count(self, hook_payload: dict[str, Any]) -> int:
        emitters = hook_payload.get("emitters", {})
        if not isinstance(emitters, dict):
            return 0
        return sum(int(item.get("fire_count", 0) or 0) for item in emitters.values() if isinstance(item, dict))

    def _safe_int(self, value: Any) -> int | None:
        if value in (None, ""):
            return None
        return int(value)

    def _select_replay_target(
        self,
        suggested_entries: list[CallbackGap],
        *,
        hook_name: str | None,
        callback_id: str | None,
    ) -> CallbackGap | None:
        for item in suggested_entries:
            if hook_name and item.hook_name == hook_name:
                return item
            if callback_id and item.callback_id == callback_id:
                return item
        return None

    def _verify_callback_covered(self, callback_id: str, wait_seconds: float) -> dict[str, Any]:
        deadline = time.time() + max(0.1, wait_seconds)
        while time.time() < deadline:
            coverage_payload = self.load_json(self.coverage_file)
            executed_entry = coverage_payload.get("data", {}).get("executed_callbacks", {}).get(callback_id, {})
            execute_count = int(executed_entry.get("executed_count", 0) or 0)
            if execute_count > 0:
                return {
                    "covered_after_replay": True,
                    "execute_count_after_replay": execute_count,
                }
            time.sleep(0.2)

        coverage_payload = self.load_json(self.coverage_file)
        executed_entry = coverage_payload.get("data", {}).get("executed_callbacks", {}).get(callback_id, {})
        return {
            "covered_after_replay": int(executed_entry.get("executed_count", 0) or 0) > 0,
            "execute_count_after_replay": int(executed_entry.get("executed_count", 0) or 0),
        }

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .models import CallbackDescriptor, RequestCallbackExecution, RequestObservation
from .state import HookEnergyDemoState


class HookCollector:
    """
    Mục đích:
    - Thu thập dữ liệu hook từ request artifacts do UOPZ export ra.
    -
    Tham số:
    - HookEnergyDemoState | None state: State toàn cục để lưu registry callback và execution count.
    -
    Giá trị trả về:
    - Không áp dụng vì đây là class collector.
    -
    Logic chính:
    - Đọc request JSON, chuẩn hóa callback identity, giữ registry active/removed,
      và chỉ giao cho calculator tập callback thực thi duy nhất của request.
    -
    Tại sao cần class này trong demo hook energy:
    - Đây là lớp tách biệt phần "collect" khỏi "score" để sau này có thể tái sử dụng
      khi tích hợp vào PHUZZ mà không viết lại logic thu thập.
    """

    def __init__(self, state: Optional[HookEnergyDemoState] = None) -> None:
        """
        Mục đích:
        - Khởi tạo collector với state có sẵn hoặc state rỗng mới.
        -
        Tham số:
        - HookEnergyDemoState | None state: State toàn cục dùng để cộng dồn thống kê.
        -
        Giá trị trả về:
        - None.
        -
        Logic chính:
        - Nếu chưa có state thì tạo mới để collector có thể chạy độc lập ngay.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Demo phải chạy được cả ở chế độ one-shot lẫn watch liên tục với cùng một API collector.
        """

        self.state = state or HookEnergyDemoState()

    def read_request_file(self, filepath: str) -> Optional[dict]:
        """
        Mục đích:
        - Đọc một request artifact JSON từ đĩa.
        -
        Tham số:
        - str filepath: Đường dẫn file request cần đọc.
        -
        Giá trị trả về:
        - Optional[dict]: Payload request nếu đọc được, ngược lại trả về None.
        -
        Logic chính:
        - Bắt lỗi JSON/file để CLI demo không chết khi gặp artifact đang ghi dở.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Runtime UOPZ có thể ghi file liên tục; collector cần đọc an toàn và bỏ qua file lỗi.
        """

        path = Path(filepath)
        if not path.exists():
            return None

        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def list_pending_request_files(self, requests_dir: str) -> list[str]:
        """
        Mục đích:
        - Liệt kê các request artifact chưa được state hiện tại xử lý.
        -
        Tham số:
        - str requests_dir: Thư mục chứa các file JSON per-request.
        -
        Giá trị trả về:
        - list[str]: Danh sách file JSON chưa có trong `processed_request_ids`.
        -
        Logic chính:
        - Lọc theo đuôi `.json`, so với state đã xử lý, rồi sort theo tên file để ổn định.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Demo cần chạy được trên thư mục output hiện có mà không double-count request cũ.
        """

        base = Path(requests_dir)
        if not base.exists():
            return []

        pending_files: list[str] = []
        for path in sorted(base.glob("*.json")):
            if path.stem in self.state.processed_request_ids:
                continue
            pending_files.append(str(path))
        return pending_files

    def collect_request(self, request_data: dict, request_file: Optional[str] = None) -> RequestObservation:
        """
        Mục đích:
        - Chuẩn hóa payload request thành `RequestObservation` để calculator dùng.
        -
        Tham số:
        - dict request_data: Dữ liệu JSON do UOPZ export cho một request.
        - Optional[str] request_file: Đường dẫn artifact tương ứng nếu có.
        -
        Giá trị trả về:
        - RequestObservation: Dữ liệu request đã được chuẩn hóa cho bước tính energy.
        -
        Logic chính:
        - Cập nhật registry từ `registered_callbacks`, sau đó lấy tập callback thực thi
          duy nhất từ `executed_callbacks` mà chưa tăng bộ đếm toàn cục.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Đây là bước biến dữ liệu runtime thô thành input sạch, dễ giải thích cho demo.
        """

        request_id = str(request_data.get("request_id", Path(request_file).stem if request_file else "unknown-request"))
        endpoint = str(request_data.get("endpoint", request_id))
        scenario_name = self._extract_scenario_name(request_data, request_id, endpoint)

        observation = RequestObservation(
            request_id=request_id,
            scenario_name=scenario_name,
            endpoint=endpoint,
            request_file=request_file,
        )

        hook_coverage = request_data.get("hook_coverage", {})
        registered_payload = hook_coverage.get("registered_callbacks", {})
        for callback_id, item in registered_payload.items():
            descriptor = self._descriptor_from_payload(str(callback_id), item)
            observation.registered_callbacks[descriptor.callback_id] = descriptor
            self._merge_descriptor_into_state(descriptor)

        executed_payload = hook_coverage.get("executed_callbacks", {})
        for callback_id, item in sorted(executed_payload.items()):
            callback_id_str = str(callback_id)
            descriptor = observation.registered_callbacks.get(callback_id_str) or self.state.callbacks.get(callback_id_str)
            if descriptor is None:
                descriptor = self._descriptor_from_payload(callback_id_str, item)

            observation.executed_callbacks.append(
                RequestCallbackExecution(
                    callback_id=callback_id_str,
                    hook_name=descriptor.hook_name,
                    callback_identity=descriptor.callback_identity,
                    priority=descriptor.priority,
                    callback_type=descriptor.callback_type,
                    request_execution_count=max(1, int(item.get("executed_count", 1))),
                )
            )

        return observation

    def finalize_request(self, report) -> None:
        """
        Mục đích:
        - Cập nhật bộ đếm toàn cục sau khi request đã được chấm điểm xong.
        -
        Tham số:
        - RequestEnergyReport report: Kết quả energy của request vừa xử lý.
        -
        Giá trị trả về:
        - None.
        -
        Logic chính:
        - Tăng `total_execution_count` bằng raw execution count của request,
          tăng `total_request_count` một lần cho mỗi callback duy nhất,
          rồi đánh dấu request là đã xử lý.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Quy tắc của demo yêu cầu phải score bằng giá trị N cũ, chỉ update state sau đó.
        """

        for item in report.executed_callbacks:
            descriptor = self.state.callbacks.get(item.callback_id)
            if descriptor is None:
                descriptor = CallbackDescriptor(
                    callback_id=item.callback_id,
                    hook_name=item.hook_name,
                    callback_identity=item.callback_identity,
                    priority=item.priority,
                    callback_type=item.callback_type,
                )
                self.state.callbacks[item.callback_id] = descriptor

            descriptor.total_execution_count += max(0, int(item.request_execution_count))
            descriptor.total_request_count += 1
            if descriptor.total_execution_count > 0:
                descriptor.status = "covered"

        self.state.processed_request_ids.add(report.request_id)

    def _descriptor_from_payload(self, callback_id: str, payload: dict) -> CallbackDescriptor:
        """
        Mục đích:
        - Tạo `CallbackDescriptor` từ dữ liệu callback trong artifact JSON.
        -
        Tham số:
        - str callback_id: ID ổn định của callback.
        - dict payload: Dữ liệu callback lấy từ `registered_callbacks` hoặc `executed_callbacks`.
        -
        Giá trị trả về:
        - CallbackDescriptor: Descriptor đã chuẩn hóa với fallback identity ổn định.
        -
        Logic chính:
        - Ưu tiên `callback_repr`; nếu thiếu thì fallback qua stable/runtime id rồi tới callback_id.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Callback identity là nền tảng để demo hiển thị rõ callback nào đang được ưu tiên.
        """

        callback_identity = self._resolve_callback_identity(callback_id, payload)
        return CallbackDescriptor(
            callback_id=callback_id,
            hook_name=str(payload.get("hook_name", payload.get("fired_hook", "unknown_hook"))),
            callback_identity=callback_identity,
            priority=int(payload.get("priority", 10)),
            callback_type=str(payload.get("callback_type", payload.get("type", "unknown"))),
            is_active=bool(payload.get("is_active", True)),
            status=str(payload.get("status", "registered_only")),
            source_file=payload.get("source_file"),
            source_line=payload.get("source_line"),
            callback_runtime_id=payload.get("callback_runtime_id"),
            stable_id=payload.get("stable_id"),
            runtime_id=payload.get("runtime_id"),
            total_execution_count=int(payload.get("total_execution_count", 0)),
            total_request_count=int(payload.get("total_request_count", 0)),
        )

    def _resolve_callback_identity(self, callback_id: str, payload: dict) -> str:
        """
        Mục đích:
        - Chuẩn hóa identity dễ đọc cho callback theo chiến lược fallback ổn định.
        -
        Tham số:
        - str callback_id: ID callback hiện tại.
        - dict payload: Dữ liệu callback chứa `callback_repr`, `stable_id`, `runtime_id`.
        -
        Giá trị trả về:
        - str: Chuỗi identity rõ ràng nhất có thể cho callback.
        -
        Logic chính:
        - Ưu tiên `callback_repr`, sau đó tới `stable_id`, `runtime_id`, rồi `callback_id`.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Một phần quan trọng của demo là giải thích "callback nào" hiếm/mới; nếu identity mơ hồ
          thì output sẽ khó đọc và khó chứng minh ý tưởng.
        """

        for key in ("callback_repr", "stable_id", "runtime_id"):
            value = str(payload.get(key, "")).strip()
            if value:
                return value
        return callback_id

    def _merge_descriptor_into_state(self, descriptor: CallbackDescriptor) -> None:
        """
        Mục đích:
        - Cập nhật registry callback toàn cục bằng descriptor mới nhất của request.
        -
        Tham số:
        - CallbackDescriptor descriptor: Callback vừa được quan sát trong request.
        -
        Giá trị trả về:
        - None.
        -
        Logic chính:
        - Nếu callback đã tồn tại thì chỉ cập nhật metadata và giữ nguyên bộ đếm toàn cục.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Demo cần nhìn được attack surface hiện tại, bao gồm callback active/removed,
          chứ không chỉ các callback đã thực thi.
        """

        existing = self.state.callbacks.get(descriptor.callback_id)
        if existing is None:
            self.state.callbacks[descriptor.callback_id] = descriptor
            return

        existing.hook_name = descriptor.hook_name
        existing.callback_identity = descriptor.callback_identity
        existing.priority = descriptor.priority
        existing.callback_type = descriptor.callback_type
        existing.is_active = descriptor.is_active
        existing.status = descriptor.status
        existing.source_file = descriptor.source_file
        existing.source_line = descriptor.source_line
        existing.callback_runtime_id = descriptor.callback_runtime_id
        existing.stable_id = descriptor.stable_id
        existing.runtime_id = descriptor.runtime_id

    def _extract_scenario_name(self, request_data: dict, request_id: str, endpoint: str) -> str:
        """
        Mục đích:
        - Suy ra tên scenario thân thiện để reporter in ra dễ hiểu hơn request_id thuần.
        -
        Tham số:
        - dict request_data: Payload request gốc.
        - str request_id: Request id nội bộ.
        - str endpoint: Endpoint đã được UOPZ suy ra.
        -
        Giá trị trả về:
        - str: Tên scenario ưu tiên theo payload/body/header nếu có.
        -
        Logic chính:
        - Ưu tiên body param `scenario`, tiếp theo là header `X-Uopz-Fuzz-Id`,
          sau đó mới fallback sang endpoint hoặc request_id.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Demo cần hiển thị "request/scenario nào" nên được ưu tiên; tên thân thiện giúp
          người xem nối kết dễ hơn với ca test thực tế.
        """

        params = request_data.get("request_params", {})
        if not isinstance(params, dict):
            params = {}

        body_params = params.get("body_params", {})
        if not isinstance(body_params, dict):
            body_params = {}

        headers = params.get("headers", {})
        if not isinstance(headers, dict):
            headers = {}

        scenario = str(body_params.get("scenario", "")).strip()
        if scenario:
            return scenario

        fuzz_id = str(headers.get("X-Uopz-Fuzz-Id", "")).strip()
        if fuzz_id:
            return fuzz_id

        if endpoint:
            return endpoint

        return request_id

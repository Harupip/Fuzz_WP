from __future__ import annotations

import json
from pathlib import Path

from .models import CallbackDescriptor


class HookEnergyDemoState:
    """
    Mục đích:
    - Lưu trạng thái toàn cục của demo hook energy qua nhiều request.
    -
    Tham số:
    - Không có tham số bắt buộc; class tự khởi tạo registry callback và tập request đã xử lý.
    -
    Giá trị trả về:
    - Không áp dụng vì đây là class trạng thái.
    -
    Logic chính:
    - Tách state ra khỏi collector/calculator để có thể lưu snapshot và khởi động lại demo.
    -
    Tại sao cần class này trong demo hook energy:
    - Demo phải chứng minh được callback nào là mới/hiếm trên toàn bộ chuỗi request,
      nên cần một state toàn cục bền vững giữa các lần chạy.
    """

    def __init__(self) -> None:
        """
        Mục đích:
        - Khởi tạo state rỗng cho registry callback và request đã xử lý.
        -
        Tham số:
        - Không có tham số đầu vào.
        -
        Giá trị trả về:
        - None.
        -
        Logic chính:
        - Dùng dict cho callback registry và set cho processed ids để tra cứu nhanh.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Đây là điểm bắt đầu gọn nhẹ cho collector khi chạy lần đầu hoặc khi reset demo.
        """

        self.callbacks: dict[str, CallbackDescriptor] = {}
        self.processed_request_ids: set[str] = set()

    def snapshot(self) -> dict:
        """
        Mục đích:
        - Chuyển toàn bộ state hiện tại sang dạng dict để ghi xuống JSON.
        -
        Tham số:
        - Không có tham số đầu vào ngoài đối tượng state hiện tại.
        -
        Giá trị trả về:
        - dict: Snapshot state gồm registry callback và processed request ids.
        -
        Logic chính:
        - Serialize từng callback descriptor bằng `to_dict` và sort request ids để output ổn định.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Demo cần giữ được history execution count giữa các lần chạy mà không phụ thuộc RAM.
        """

        return {
            "schema_version": "hook-energy-demo-state-v1",
            "callbacks": {callback_id: item.to_dict() for callback_id, item in sorted(self.callbacks.items())},
            "processed_request_ids": sorted(self.processed_request_ids),
        }

    def save(self, filepath: str) -> None:
        """
        Mục đích:
        - Ghi snapshot state hiện tại xuống file JSON một cách an toàn.
        -
        Tham số:
        - str filepath: Đường dẫn file snapshot cần ghi.
        -
        Giá trị trả về:
        - None.
        -
        Logic chính:
        - Tạo thư mục cha nếu cần, ghi ra file tạm, rồi thay thế atomically.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Demo phải có trạng thái bền để tiếp tục đếm callback hiếm/mới mà không bị mất dữ liệu.
        """

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(self.snapshot(), indent=2, ensure_ascii=False)
        path.write_text(content, encoding="utf-8")

    @classmethod
    def load(cls, filepath: str) -> "HookEnergyDemoState":
        """
        Mục đích:
        - Tạo state từ file snapshot đã lưu trước đó nếu file tồn tại.
        -
        Tham số:
        - str filepath: Đường dẫn snapshot cần nạp.
        -
        Giá trị trả về:
        - HookEnergyDemoState: State đã nạp dữ liệu hoặc state rỗng nếu file chưa có.
        -
        Logic chính:
        - Đọc JSON, khôi phục processed ids, và dựng lại từng callback descriptor.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Cho phép CLI demo chạy nhiều lần mà vẫn giữ được lịch sử hiếm/phổ biến của callback.
        """

        path = Path(filepath)
        state = cls()
        if not path.exists():
            return state

        payload = json.loads(path.read_text(encoding="utf-8"))
        for callback_id, item in payload.get("callbacks", {}).items():
            state.callbacks[callback_id] = CallbackDescriptor(
                callback_id=callback_id,
                hook_name=str(item.get("hook_name", "")),
                callback_identity=str(item.get("callback_identity", item.get("callback_repr", callback_id))),
                priority=int(item.get("priority", 10)),
                callback_type=str(item.get("callback_type", item.get("type", "unknown"))),
                is_active=bool(item.get("is_active", True)),
                status=str(item.get("status", "registered_only")),
                source_file=item.get("source_file"),
                source_line=item.get("source_line"),
                callback_runtime_id=item.get("callback_runtime_id"),
                stable_id=item.get("stable_id"),
                runtime_id=item.get("runtime_id"),
                total_execution_count=int(item.get("total_execution_count", 0)),
                total_request_count=int(item.get("total_request_count", 0)),
            )

        state.processed_request_ids = {str(item) for item in payload.get("processed_request_ids", [])}
        return state

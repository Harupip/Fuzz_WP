from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CallbackDescriptor:
    """
    Mục đích:
    - Đại diện cho một callback đã được đăng ký trong runtime WordPress.
    -
    Tham số:
    - Các field lưu thông tin định danh callback, hook, priority, trạng thái active,
      và thống kê thực thi toàn cục.
    -
    Giá trị trả về:
    - Không áp dụng vì đây là dataclass dùng để đóng gói dữ liệu.
    -
    Logic chính:
    - Giữ chung dữ liệu đăng ký, dữ liệu thực thi, và bộ đếm toàn cục ở một chỗ.
    -
    Tại sao cần class này trong demo hook energy:
    - Demo cần một identity ổn định để vừa log dễ đọc vừa cộng dồn execution count
      chính xác qua nhiều request.
    """

    callback_id: str
    hook_name: str
    callback_identity: str
    priority: int
    callback_type: str
    is_active: bool = True
    status: str = "registered_only"
    source_file: Optional[str] = None
    source_line: Optional[int] = None
    callback_runtime_id: Optional[str] = None
    stable_id: Optional[str] = None
    runtime_id: Optional[str] = None
    total_execution_count: int = 0
    total_request_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """
        Mục đích:
        - Chuyển callback descriptor sang dict để ghi JSON snapshot hoặc report.
        -
        Tham số:
        - Không có tham số đầu vào ngoài chính đối tượng hiện tại.
        -
        Giá trị trả về:
        - dict[str, Any]: Dữ liệu callback ở dạng thuần JSON.
        -
        Logic chính:
        - Sao chép toàn bộ field quan trọng và bổ sung `identity_label` dễ đọc.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Demo cần export state và report để người xem kiểm tra trực tiếp từng callback.
        """

        return {
            "callback_id": self.callback_id,
            "hook_name": self.hook_name,
            "callback_identity": self.callback_identity,
            "identity_label": f"{self.hook_name} :: {self.callback_identity} :: priority={self.priority}",
            "priority": self.priority,
            "callback_type": self.callback_type,
            "is_active": self.is_active,
            "status": self.status,
            "source_file": self.source_file,
            "source_line": self.source_line,
            "callback_runtime_id": self.callback_runtime_id,
            "stable_id": self.stable_id,
            "runtime_id": self.runtime_id,
            "total_execution_count": self.total_execution_count,
            "total_request_count": self.total_request_count,
        }


@dataclass
class RequestCallbackExecution:
    """
    Mục đích:
    - Đại diện cho một callback đã thực thi trong một request cụ thể.
    -
    Tham số:
    - Các field mô tả callback, số lần chạy trong request, số lần đã chạy trước đó,
      và điểm hook_score tương ứng.
    -
    Giá trị trả về:
    - Không áp dụng vì đây là dataclass chứa dữ liệu.
    -
    Logic chính:
    - Tách riêng dữ liệu theo request để energy calculator không phụ thuộc state nội bộ.
    -
    Tại sao cần class này trong demo hook energy:
    - Demo cần in ra rõ callback nào làm request trở nên quan trọng hơn và vì sao.
    """

    callback_id: str
    hook_name: str
    callback_identity: str
    priority: int
    callback_type: str
    request_execution_count: int
    previous_execution_count: int = 0
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """
        Mục đích:
        - Chuyển callback execution của request sang dict để reporter và JSON dùng lại.
        -
        Tham số:
        - Không có tham số đầu vào ngoài đối tượng hiện tại.
        -
        Giá trị trả về:
        - dict[str, Any]: Dữ liệu callback execution ở dạng JSON-friendly.
        -
        Logic chính:
        - Ghi cả `previous_execution_count` lẫn `request_execution_count` để đối chiếu
          đúng với công thức 1 / (N + 1).
        -
        Tại sao cần hàm này trong demo hook energy:
        - Đây là thông tin lõi để giải thích tại sao request nhận energy cao hay thấp.
        """

        return {
            "callback_id": self.callback_id,
            "hook_name": self.hook_name,
            "callback_identity": self.callback_identity,
            "identity_label": f"{self.hook_name} :: {self.callback_identity} :: priority={self.priority}",
            "priority": self.priority,
            "callback_type": self.callback_type,
            "request_execution_count": self.request_execution_count,
            "previous_execution_count": self.previous_execution_count,
            "score": self.score,
        }


@dataclass
class RequestObservation:
    """
    Mục đích:
    - Gom dữ liệu thô của một request sau khi collector đọc JSON artifact.
    -
    Tham số:
    - request_id, scenario_name, endpoint, danh sách callback đăng ký, và danh sách
      callback thực thi duy nhất trong request.
    -
    Giá trị trả về:
    - Không áp dụng vì đây là dataclass trung gian.
    -
    Logic chính:
    - Tách bước thu thập khỏi bước tính điểm để module sau này dễ cắm vào PHUZZ.
    -
    Tại sao cần class này trong demo hook energy:
    - Demo cần luồng rõ ràng collector -> calculator -> reporter, không trộn trách nhiệm.
    """

    request_id: str
    scenario_name: str
    endpoint: str
    request_file: Optional[str] = None
    registered_callbacks: dict[str, CallbackDescriptor] = field(default_factory=dict)
    executed_callbacks: list[RequestCallbackExecution] = field(default_factory=list)


@dataclass
class RequestEnergyReport:
    """
    Mục đích:
    - Đóng gói kết quả energy của một request sau khi calculator xử lý.
    -
    Tham số:
    - request_id, scenario_name, endpoint, danh sách callback đã chấm điểm,
      `hook_energy`, và `hook_energy_avg`.
    -
    Giá trị trả về:
    - Không áp dụng vì đây là dataclass kết quả.
    -
    Logic chính:
    - Giữ cả kết quả mặc định (`max`) và số đo phụ (`avg`) để debug thuận tiện.
    -
    Tại sao cần class này trong demo hook energy:
    - Mục tiêu của demo là cho thấy request nào đáng ưu tiên hơn, nên cần một cấu trúc
      kết quả rõ ràng để log, xếp hạng, và export.
    """

    request_id: str
    scenario_name: str
    endpoint: str
    request_file: Optional[str]
    executed_callbacks: list[RequestCallbackExecution] = field(default_factory=list)
    hook_energy: float = 0.0
    hook_energy_avg: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """
        Mục đích:
        - Chuyển báo cáo energy của request sang dict để ghi file report tổng hợp.
        -
        Tham số:
        - Không có tham số đầu vào ngoài chính kết quả hiện tại.
        -
        Giá trị trả về:
        - dict[str, Any]: Báo cáo request ở dạng JSON-friendly.
        -
        Logic chính:
        - Ghi đầy đủ thông tin request và danh sách callback đã được chấm điểm.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Demo cần cả console output lẫn artifact JSON để dễ trình bày và kiểm chứng.
        """

        return {
            "request_id": self.request_id,
            "scenario_name": self.scenario_name,
            "endpoint": self.endpoint,
            "request_file": self.request_file,
            "hook_energy": self.hook_energy,
            "hook_energy_avg": self.hook_energy_avg,
            "executed_callbacks": [item.to_dict() for item in self.executed_callbacks],
        }

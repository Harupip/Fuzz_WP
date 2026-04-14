from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SeedRequestTemplate:
    """
    Mục đích:
    - Đại diện cho seed HTTP tối thiểu được suy ra từ hook WordPress.
    -
    Tham số:
    - method, path, content_type, body, auth_mode mô tả request có thể replay.
    -
    Giá trị trả về:
    - Không áp dụng vì đây là dataclass dùng để đóng gói dữ liệu.
    -
    Logic chính:
    - Giữ seed ở dạng thuần dữ liệu để sau này PHUZZ hoặc tool khác có thể đọc lại dễ dàng.
    -
    Vì sao cần nó trong pipeline seed generation:
    - Seed ở giai đoạn này chỉ là điểm chạm tối thiểu để đi vào callback, chưa phải payload fuzz hoàn chỉnh.
    """

    method: str
    path: str
    content_type: str
    body: dict[str, Any] = field(default_factory=dict)
    auth_mode: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "path": self.path,
            "content_type": self.content_type,
            "body": self.body,
            "auth_mode": self.auth_mode,
        }


@dataclass
class CallbackGap:
    """
    Mục đích:
    - Đóng gói một callback trong báo cáo gap/candidate seed.
    -
    Tham số:
    - Lưu cả metadata raw từ runtime lẫn kết quả chuẩn hóa phục vụ seed generation.
    -
    Giá trị trả về:
    - Không áp dụng vì đây là dataclass dữ liệu.
    -
    Logic chính:
    - Giữ chung thông tin callback, coverage status, mức ưu tiên seed, và seed template suy ra được.
    -
    Vì sao cần nó trong pipeline seed generation:
    - Pipeline cần một cấu trúc ổn định để vừa ghi JSON, vừa replay, vừa làm adapter cho PHUZZ về sau.
    """

    callback_id: str
    hook_name: str
    callback_name: str
    callback_raw: str
    callback_type: str
    priority: int
    accepted_args: int
    source_file: str | None
    source_line: int | None
    is_active: bool
    registration_status: str
    register_count: int
    execute_count: int
    status: str
    seed_priority: str
    priority_rank: int
    target_family: str
    direct_http_supported: bool
    generation_status: str
    notes: list[str] = field(default_factory=list)
    seed: SeedRequestTemplate | None = None
    hook_fire_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "callback_id": self.callback_id,
            "hook_name": self.hook_name,
            "callback_name": self.callback_name,
            "callback_raw": self.callback_raw,
            "callback_type": self.callback_type,
            "priority": self.priority,
            "accepted_args": self.accepted_args,
            "source_file": self.source_file,
            "source_line": self.source_line,
            "is_active": self.is_active,
            "registration_status": self.registration_status,
            "register_count": self.register_count,
            "execute_count": self.execute_count,
            "status": self.status,
            "seed_priority": self.seed_priority,
            "priority_rank": self.priority_rank,
            "target_family": self.target_family,
            "direct_http_supported": self.direct_http_supported,
            "generation_status": self.generation_status,
            "hook_fire_count": self.hook_fire_count,
            "notes": list(self.notes),
            "seed": self.seed.to_dict() if self.seed is not None else None,
        }

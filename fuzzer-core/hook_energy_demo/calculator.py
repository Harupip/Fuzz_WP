from __future__ import annotations

from .collector import HookCollector
from .models import RequestCallbackExecution, RequestEnergyReport, RequestObservation


class HookEnergyCalculator:
    """
    Mục đích:
    - Tính hook score và request-level hook energy cho demo standalone.
    -
    Tham số:
    - Không có tham số bắt buộc vì demo dùng công thức cố định 1 / (N + 1).
    -
    Giá trị trả về:
    - Không áp dụng vì đây là class calculator.
    -
    Logic chính:
    - Đọc bộ đếm toàn cục hiện tại từ collector, chấm điểm từng callback thực thi duy nhất,
      sau đó aggregate mặc định bằng `max`.
    -
    Tại sao cần class này trong demo hook energy:
    - Giữ phần toán học tách biệt giúp chứng minh ý tưởng dễ hơn và sẵn sàng tái sử dụng
      khi tích hợp vào PHUZZ về sau.
    """

    def score_callback(self, previous_execution_count: int) -> float:
        """
        Mục đích:
        - Tính điểm hook_score cho một callback theo công thức demo 1 / (N + 1).
        -
        Tham số:
        - int previous_execution_count: Số lần callback đã thực thi trước request hiện tại.
        -
        Giá trị trả về:
        - float: Điểm trong khoảng (0, 1], với callback mới là 1.0.
        -
        Logic chính:
        - Chuẩn hóa `N` về không âm rồi áp dụng trực tiếp công thức của đề bài.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Đây là lõi để chứng minh callback mới hoặc hiếm phải được ưu tiên cao hơn.
        """

        safe_count = max(0, int(previous_execution_count))
        return 1.0 / float(safe_count + 1)

    def calculate_request_energy(self, observation: RequestObservation, collector: HookCollector) -> RequestEnergyReport:
        """
        Mục đích:
        - Tính toàn bộ energy report cho một request từ dữ liệu collector và state hiện tại.
        -
        Tham số:
        - RequestObservation observation: Dữ liệu request đã được chuẩn hóa.
        - HookCollector collector: Collector đang giữ state execution count toàn cục.
        -
        Giá trị trả về:
        - RequestEnergyReport: Báo cáo energy hoàn chỉnh của request.
        -
        Logic chính:
        - Lấy `N` từ state trước khi finalize request, chấm điểm từng callback duy nhất,
          rồi tính `max` làm energy mặc định và `avg` làm số đo phụ.
        -
        Tại sao cần hàm này trong demo hook energy:
        - Đây là bước biến raw hook coverage thành tín hiệu ưu tiên request dễ giải thích.
        """

        scored_callbacks: list[RequestCallbackExecution] = []
        total_score = 0.0
        max_score = 0.0

        for item in observation.executed_callbacks:
            existing = collector.state.callbacks.get(item.callback_id)
            previous_execution_count = int(existing.total_execution_count) if existing is not None else 0
            score = self.score_callback(previous_execution_count)

            scored_callbacks.append(
                RequestCallbackExecution(
                    callback_id=item.callback_id,
                    hook_name=item.hook_name,
                    callback_identity=item.callback_identity,
                    priority=item.priority,
                    callback_type=item.callback_type,
                    request_execution_count=item.request_execution_count,
                    previous_execution_count=previous_execution_count,
                    score=score,
                )
            )
            total_score += score
            max_score = max(max_score, score)

        hook_energy_avg = total_score / len(scored_callbacks) if scored_callbacks else 0.0
        return RequestEnergyReport(
            request_id=observation.request_id,
            scenario_name=observation.scenario_name,
            endpoint=observation.endpoint,
            request_file=observation.request_file,
            executed_callbacks=scored_callbacks,
            hook_energy=max_score if scored_callbacks else 0.0,
            hook_energy_avg=hook_energy_avg,
        )

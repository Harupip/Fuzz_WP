from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Tuple

from .calculator import EnergyCalculator
from .config import EnergyConfig
from .models import EnergyResult
from .request_store import find_new_request_files, read_request_file
from .state import GlobalCoverageState


class EnergyScheduler:
    def __init__(
        self,
        requests_dir: str = "/var/www/uopz/output/requests",
        snapshot_path: str = "/var/www/uopz/output/energy_state.json",
        config: Optional[EnergyConfig] = None,
        snapshot_interval: int = 50,
    ):
        self.requests_dir = requests_dir
        self.snapshot_path = snapshot_path
        self.snapshot_interval = snapshot_interval
        self.calculator = EnergyCalculator(config)
        self.processed_ids: set = set()
        self._requests_since_snapshot = 0

    @property
    def state(self) -> GlobalCoverageState:
        return self.calculator.state

    def load_previous_state(self) -> bool:
        if os.path.exists(self.snapshot_path):
            self.calculator.state.load_snapshot(self.snapshot_path)
            return True
        return False

    def save_state(self) -> None:
        self.calculator.state.save_snapshot(self.snapshot_path)

    def process_request_file(self, filepath: str) -> Optional[EnergyResult]:
        data = read_request_file(filepath)
        if data is None:
            return None

        req_id = data.get("request_id", Path(filepath).stem)
        if req_id in self.processed_ids:
            return None

        result = self.calculator.process_request(data)
        self.processed_ids.add(req_id)
        self._requests_since_snapshot += 1

        if self._requests_since_snapshot >= self.snapshot_interval:
            self.save_state()
            self._requests_since_snapshot = 0

        return result

    def process_new_requests(self) -> List[Tuple[str, EnergyResult]]:
        new_files = find_new_request_files(self.requests_dir, self.processed_ids)
        results = []
        for filepath in new_files:
            req_id = Path(filepath).stem
            result = self.process_request_file(filepath)
            if result is not None:
                results.append((req_id, result))
        return results

    def get_energy_for_request(self, request_data: dict) -> EnergyResult:
        return self.calculator.process_request(request_data)

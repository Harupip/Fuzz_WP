"""
Energy-Based Scheduling cho Fuzz_WP.

Thay the hoan toan hook_energy.php.
PHP side chi can ghi raw hook_coverage vao per-request JSON.
Python fuzzer doc file do roi tinh energy in-memory.

Cach dung:
    from energy import EnergyCalculator, EnergyConfig

    calc = EnergyCalculator()                    # mac dinh doc env
    calc = EnergyCalculator(EnergyConfig(...))    # hoac truyen truc tiep

    # Trong vong lap fuzzer:
    request_data = json.load(open(request_file))
    result = calc.process_request(request_data)
    energy_score = result.score          # int >= 1
    tier = result.dominant_tier          # 'first_seen' | 'rare' | 'frequent' | 'no_coverage'
"""

from __future__ import annotations

import json
import os
import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIG
# =============================================================================

@dataclass
class EnergyConfig:
    """
    Tham so energy, tuong duong getenv() trong PHP hook_energy.php.
    Co the truyen truc tiep hoac doc tu environment variables.
    """

    # --- Tier weights (giong hook_energy.php) ---
    callback_first_seen: int = 12
    callback_rare: int = 5
    callback_frequent: int = 1

    # --- Threshold ---
    rare_max_count: int = 3

    # --- MO RONG: bonuses cho smart scheduling ---
    blindspot_bonus: int = 8       # Bonus khi request trigger callback chua bao gio executed
    new_hook_bonus: int = 10       # Bonus khi request trigger hook_name chua tung thay
    coverage_delta_weight: float = 2.0  # (reserved) nhan he so khi coverage tang them

    # --- Clamp ---
    max_energy: int = 200          # Gioi han tren de tranh budget explosion

    @classmethod
    def from_env(cls) -> EnergyConfig:
        """Doc config tu environment variables (tuong thich voi PHP version)."""

        def _env_int(name: str, default: int) -> int:
            val = os.environ.get(name, "")
            return int(val) if val.isdigit() else default

        def _env_float(name: str, default: float) -> float:
            val = os.environ.get(name, "")
            try:
                return float(val) if val else default
            except ValueError:
                return default

        return cls(
            callback_first_seen=_env_int("FUZZER_ENERGY_CALLBACK_FIRST", 12),
            callback_rare=_env_int("FUZZER_ENERGY_CALLBACK_RARE", 5),
            callback_frequent=_env_int("FUZZER_ENERGY_CALLBACK_FREQUENT", 1),
            rare_max_count=_env_int("FUZZER_ENERGY_RARE_CALLBACK_MAX", 3),
            blindspot_bonus=_env_int("FUZZER_ENERGY_BLINDSPOT_BONUS", 8),
            new_hook_bonus=_env_int("FUZZER_ENERGY_NEW_HOOK_BONUS", 10),
            coverage_delta_weight=_env_float("FUZZER_ENERGY_COVERAGE_DELTA_WEIGHT", 2.0),
            max_energy=_env_int("FUZZER_ENERGY_MAX", 200),
        )


# =============================================================================
# RESULT
# =============================================================================

@dataclass
class EnergyResult:
    """Ket qua tinh energy cho mot request."""

    score: int = 1
    dominant_tier: str = "no_coverage"

    # Chi tiet tung tier
    first_seen_count: int = 0
    rare_count: int = 0
    frequent_count: int = 0

    # Bonuses
    blindspot_hits: int = 0
    new_hooks_discovered: int = 0

    # Chi tiet items (optional, de debug)
    components: Dict[str, list] = field(default_factory=lambda: {
        "first_seen": [],
        "rare": [],
        "frequent": [],
    })

    def to_dict(self) -> dict:
        """Serialize de ghi JSON debug."""
        return {
            "score": self.score,
            "dominant_tier": self.dominant_tier,
            "first_seen_count": self.first_seen_count,
            "rare_count": self.rare_count,
            "frequent_count": self.frequent_count,
            "blindspot_hits": self.blindspot_hits,
            "new_hooks_discovered": self.new_hooks_discovered,
            "summary": {
                "first_seen_items": len(self.components.get("first_seen", [])),
                "rare_items": len(self.components.get("rare", [])),
                "frequent_items": len(self.components.get("frequent", [])),
            },
        }


# =============================================================================
# GLOBAL STATE (IN-MEMORY)
# =============================================================================

class GlobalCoverageState:
    """
    Luu trang thai coverage tich luy in-memory.
    Thay the hoan toan viec doc/ghi total_coverage.json moi request.

    State nay duoc duy tri suot session fuzzing.
    Khi can persist (cho restart/debug), goi snapshot() de ghi file.
    """

    def __init__(self):
        # callback_id -> tong so lan executed qua tat ca requests
        self.executed_counts: Dict[str, int] = {}

        # callback_id -> thong tin callback (lay tu request dau tien thay no)
        self.registered_callbacks: Dict[str, dict] = {}

        # callback_id -> thong tin executed callback
        self.executed_callbacks: Dict[str, dict] = {}

        # Tap hop hook_names da thay
        self.seen_hooks: set = set()

        # Thong ke tong
        self.total_requests: int = 0
        self.start_time: float = time.time()

    @property
    def blindspot_ids(self) -> set:
        """Tap callback_id da register nhung chua bao gio executed."""
        return set(self.registered_callbacks.keys()) - set(self.executed_counts.keys())

    @property
    def coverage_percent(self) -> float:
        """Ty le callback da covered."""
        total = len(self.registered_callbacks)
        if total == 0:
            return 0.0
        covered = len(set(self.executed_counts.keys()) & set(self.registered_callbacks.keys()))
        return round(covered / total * 100, 2)

    def update_from_request(self, request_data: dict) -> None:
        """Cap nhat global state tu raw request coverage data."""
        self.total_requests += 1
        hook_cov = request_data.get("hook_coverage", {})

        # Merge registered callbacks
        for cb_id, info in hook_cov.get("registered_callbacks", {}).items():
            if cb_id not in self.registered_callbacks:
                self.registered_callbacks[cb_id] = info
            hook_name = info.get("hook_name", "")
            if hook_name:
                self.seen_hooks.add(hook_name)

        # Merge executed callbacks
        for cb_id, info in hook_cov.get("executed_callbacks", {}).items():
            count = int(info.get("executed_count", 1))
            self.executed_counts[cb_id] = self.executed_counts.get(cb_id, 0) + count

            # Luu/cap nhat execution info
            if cb_id not in self.executed_callbacks:
                self.executed_callbacks[cb_id] = info.copy()
            else:
                existing = self.executed_callbacks[cb_id]
                existing["executed_count"] = self.executed_counts[cb_id]
                if "last_seen" in info:
                    existing["last_seen"] = info["last_seen"]
                if "fired_hook" in info:
                    existing["fired_hook"] = info["fired_hook"]
                if "request_id" in info:
                    existing["request_id"] = info["request_id"]
                if "endpoint" in info:
                    existing["endpoint"] = info["endpoint"]

            hook_name = info.get("hook_name", "")
            if hook_name:
                self.seen_hooks.add(hook_name)

    def get_historical_count(self, callback_id: str) -> int:
        """Lay so lan callback da duoc executed truoc do."""
        return self.executed_counts.get(callback_id, 0)

    def is_blindspot(self, callback_id: str) -> bool:
        """Callback da register nhung chua tung duoc executed."""
        return (
            callback_id in self.registered_callbacks
            and callback_id not in self.executed_counts
        )

    def is_new_hook(self, hook_name: str) -> bool:
        """Hook name chua tung xuat hien."""
        return hook_name not in self.seen_hooks

    def snapshot(self) -> dict:
        """
        Xuat snapshot trang thai hien tai.
        Tuong thich voi format total_coverage.json cu de debug.
        """
        covered_executed = {}
        blindspots = {}

        for cb_id, info in self.registered_callbacks.items():
            if cb_id in self.executed_counts:
                covered_executed[cb_id] = self.executed_callbacks.get(cb_id, info)
            else:
                blindspots[cb_id] = info

        total_reg = len(self.registered_callbacks)
        total_exec = len(covered_executed)

        return {
            "metadata": {
                "total_registered_callbacks": total_reg,
                "total_executed_callbacks": total_exec,
                "coverage_percent": f"{self.coverage_percent}%",
                "total_requests_processed": self.total_requests,
                "total_blindspots": len(blindspots),
                "uptime_seconds": round(time.time() - self.start_time, 2),
            },
            "data": {
                "registered_callbacks": self.registered_callbacks,
                "executed_callbacks": covered_executed,
                "blindspot_callbacks": blindspots,
            },
        }

    def save_snapshot(self, filepath: str) -> None:
        """Ghi snapshot ra file JSON (atomic write)."""
        data = self.snapshot()
        tmp = filepath + f".tmp.{os.getpid()}"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            # Atomic rename (POSIX) / replace (Windows)
            if os.name == "nt":
                if os.path.exists(filepath):
                    os.remove(filepath)
            os.rename(tmp, filepath)
        except OSError:
            logger.exception("Failed to save snapshot to %s", filepath)
            if os.path.exists(tmp):
                os.remove(tmp)

    def load_snapshot(self, filepath: str) -> None:
        """
        Khoi phuc state tu file snapshot (cho warm restart).
        Goi ham nay TRUOC khi bat dau fuzzing neu muon tiep tuc session cu.
        """
        if not os.path.exists(filepath):
            logger.warning("Snapshot file not found: %s", filepath)
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            logger.exception("Failed to load snapshot from %s", filepath)
            return

        payload = data.get("data", {})

        for cb_id, info in payload.get("registered_callbacks", {}).items():
            if cb_id not in self.registered_callbacks:
                self.registered_callbacks[cb_id] = info
            hook_name = info.get("hook_name", "")
            if hook_name:
                self.seen_hooks.add(hook_name)

        for cb_id, info in payload.get("executed_callbacks", {}).items():
            count = int(info.get("executed_count", 0))
            self.executed_counts[cb_id] = self.executed_counts.get(cb_id, 0) + count
            if cb_id not in self.executed_callbacks:
                self.executed_callbacks[cb_id] = info.copy()
            hook_name = info.get("hook_name", "")
            if hook_name:
                self.seen_hooks.add(hook_name)

        logger.info(
            "Loaded snapshot: %d registered, %d executed, %.1f%% coverage",
            len(self.registered_callbacks),
            len(self.executed_counts),
            self.coverage_percent,
        )


# =============================================================================
# ENERGY CALCULATOR
# =============================================================================

class EnergyCalculator:
    """
    Tinh energy score cho moi request.
    Thay the hoan toan __uopz_fuzz_calculate_request_energy() trong PHP.

    Usage:
        calc = EnergyCalculator()

        # Trong fuzzer loop:
        result = calc.process_request(request_data)
        for i in range(result.score):
            mutated = mutate(candidate)
            ...
    """

    def __init__(self, config: Optional[EnergyConfig] = None):
        self.config = config or EnergyConfig.from_env()
        self.state = GlobalCoverageState()

        # Internal stats
        self._total_energy_computed = 0
        self._request_count = 0

    def _classify_tier(self, historical_count: int) -> str:
        """Phan loai callback vao tier dua tren lich su."""
        if historical_count <= 0:
            return "first_seen"
        if historical_count <= self.config.rare_max_count:
            return "rare"
        return "frequent"

    def _tier_weight(self, tier: str) -> int:
        """Lay weight tuong ung cho tier."""
        weights = {
            "first_seen": self.config.callback_first_seen,
            "rare": self.config.callback_rare,
            "frequent": self.config.callback_frequent,
        }
        return weights.get(tier, 1)

    def calculate(self, request_data: dict) -> EnergyResult:
        """
        Tinh energy tu raw request data.

        QUAN TRONG: Goi ham nay TRUOC khi goi state.update_from_request()
        de so sanh current vs historical chinh xac.
        """
        hook_cov = request_data.get("hook_coverage", {})
        executed = hook_cov.get("executed_callbacks", {})

        result = EnergyResult()
        total_energy = 0

        for cb_id, info in executed.items():
            hist_count = self.state.get_historical_count(cb_id)
            tier = self._classify_tier(hist_count)
            weight = self._tier_weight(tier)
            total_energy += weight

            # Ghi nhan tier counts
            if tier == "first_seen":
                result.first_seen_count += 1
            elif tier == "rare":
                result.rare_count += 1
            else:
                result.frequent_count += 1

            # Component detail (de debug)
            hook_name = info.get("hook_name", "unknown")
            callback_repr = info.get("callback_repr", "unknown_callback")

            result.components[tier].append({
                "callback_id": cb_id,
                "hook_name": hook_name,
                "callback_repr": callback_repr,
                "previous_executed_count": hist_count,
                "request_executed_count": int(info.get("executed_count", 1)),
                "energy": weight,
            })

            # Bonus: blindspot callback vua duoc trigger
            if self.state.is_blindspot(cb_id):
                total_energy += self.config.blindspot_bonus
                result.blindspot_hits += 1

            # Bonus: hook moi chua tung thay
            if hook_name and self.state.is_new_hook(hook_name):
                total_energy += self.config.new_hook_bonus
                result.new_hooks_discovered += 1

        # Xac dinh dominant tier (uu tien first_seen > rare > frequent)
        for tier_name in ("first_seen", "rare", "frequent"):
            count = getattr(result, f"{tier_name}_count", 0)
            if count > 0:
                result.dominant_tier = tier_name
                break

        # Clamp energy
        result.score = max(1, min(total_energy, self.config.max_energy))

        return result

    def process_request(self, request_data: dict) -> EnergyResult:
        """
        Convenience method: tinh energy roi cap nhat state.
        Day la ham chinh ma fuzzer loop se goi.

        Args:
            request_data: Raw request JSON tu PHP
                          (phai co key 'hook_coverage')

        Returns:
            EnergyResult voi score >= 1
        """
        energy = self.calculate(request_data)
        self.state.update_from_request(request_data)

        self._request_count += 1
        self._total_energy_computed += energy.score

        return energy

    def get_stats(self) -> dict:
        """Thong ke hieu suat cua calculator."""
        return {
            "requests_processed": self._request_count,
            "total_energy_computed": self._total_energy_computed,
            "avg_energy_per_request": (
                round(self._total_energy_computed / self._request_count, 2)
                if self._request_count > 0 else 0
            ),
            "coverage": self.state.coverage_percent,
            "total_registered": len(self.state.registered_callbacks),
            "total_executed": len(self.state.executed_counts),
            "total_blindspots": len(self.state.blindspot_ids),
        }


# =============================================================================
# REQUEST FILE READER
# =============================================================================

def read_request_file(filepath: str) -> Optional[dict]:
    """
    Doc per-request JSON file ma PHP vua ghi.
    Tra ve None neu file khong ton tai hoac loi.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to read request file %s: %s", filepath, e)
        return None


def find_new_request_files(
    requests_dir: str,
    processed_ids: set,
) -> List[str]:
    """
    Tim cac request file moi chua duoc xu ly.

    Args:
        requests_dir: Thu muc chua per-request JSON files
        processed_ids: Tap request_id da xu ly (de skip)

    Returns:
        Danh sach file paths moi.
    """
    if not os.path.isdir(requests_dir):
        return []

    new_files = []
    for filename in os.listdir(requests_dir):
        if not filename.endswith(".json"):
            continue
        # request_id la ten file khong co .json
        req_id = filename[:-5]
        if req_id in processed_ids:
            continue
        new_files.append(os.path.join(requests_dir, filename))

    return sorted(new_files)


# =============================================================================
# CONVENIENCE: ALL-IN-ONE FUZZER INTEGRATION
# =============================================================================

class EnergyScheduler:
    """
    High-level wrapper tich hop vao fuzzer loop.

    Cung cap:
    - Tu dong doc per-request files tu PHP
    - Tinh energy va tra ve ket qua
    - Periodic snapshot de debug
    - Warm restart tu snapshot cu

    Usage:
        scheduler = EnergyScheduler(
            requests_dir="/var/www/uopz/output/requests",
            snapshot_path="/var/www/uopz/output/total_coverage.json",
        )

        # Optional: warm restart
        scheduler.load_previous_state()

        # Trong fuzzer loop:
        new_results = scheduler.process_new_requests()
        for req_id, energy_result in new_results:
            print(f"Request {req_id}: energy={energy_result.score}")

        # Periodic save
        scheduler.save_state()
    """

    def __init__(
        self,
        requests_dir: str = "/var/www/uopz/output/requests",
        snapshot_path: str = "/var/www/uopz/output/total_coverage.json",
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
        """Load state tu snapshot file (warm restart)."""
        if os.path.exists(self.snapshot_path):
            self.calculator.state.load_snapshot(self.snapshot_path)
            return True
        return False

    def save_state(self) -> None:
        """Ghi snapshot hien tai ra file."""
        self.calculator.state.save_snapshot(self.snapshot_path)

    def process_request_file(self, filepath: str) -> Optional[EnergyResult]:
        """Xu ly mot request file va tra ve energy result."""
        data = read_request_file(filepath)
        if data is None:
            return None

        req_id = data.get("request_id", Path(filepath).stem)
        if req_id in self.processed_ids:
            return None

        result = self.calculator.process_request(data)
        self.processed_ids.add(req_id)

        # Auto snapshot
        self._requests_since_snapshot += 1
        if self._requests_since_snapshot >= self.snapshot_interval:
            self.save_state()
            self._requests_since_snapshot = 0

        return result

    def process_new_requests(self) -> List[tuple]:
        """
        Scan thu muc requests, xu ly cac file moi.

        Returns:
            List of (request_id, EnergyResult) tuples
        """
        new_files = find_new_request_files(self.requests_dir, self.processed_ids)
        results = []

        for filepath in new_files:
            req_id = Path(filepath).stem
            result = self.process_request_file(filepath)
            if result is not None:
                results.append((req_id, result))

        return results

    def get_energy_for_request(self, request_data: dict) -> EnergyResult:
        """
        Tinh energy truc tiep tu request data dict.
        Khong can doc file - dung khi fuzzer da co data trong memory.
        """
        return self.calculator.process_request(request_data)

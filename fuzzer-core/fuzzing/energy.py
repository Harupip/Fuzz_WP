"""
Compatibility wrapper that exposes the modular implementation in `energy/`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

_PACKAGE_INIT = Path(__file__).with_name("energy") / "__init__.py"
_SPEC = importlib.util.spec_from_file_location(
    "_energy_package",
    _PACKAGE_INIT,
    submodule_search_locations=[str(_PACKAGE_INIT.parent)],
)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Cannot load energy package from {_PACKAGE_INIT}")

_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules["_energy_package"] = _MODULE
_SPEC.loader.exec_module(_MODULE)

EnergyCalculator = _MODULE.EnergyCalculator
EnergyConfig = _MODULE.EnergyConfig
EnergyResult = _MODULE.EnergyResult
EnergyScheduler = _MODULE.EnergyScheduler
GlobalCoverageState = _MODULE.GlobalCoverageState

__all__ = [
    "EnergyCalculator",
    "EnergyConfig",
    "EnergyResult",
    "EnergyScheduler",
    "GlobalCoverageState",
]

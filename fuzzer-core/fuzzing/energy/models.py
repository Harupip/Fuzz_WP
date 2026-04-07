from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class EnergyResult:
    score: int = 1
    dominant_tier: str = "no_coverage"
    first_seen_count: int = 0
    rare_count: int = 0
    frequent_count: int = 0
    blindspot_hits: int = 0
    new_hooks_discovered: int = 0
    components: Dict[str, list] = field(default_factory=lambda: {
        "first_seen": [],
        "rare": [],
        "frequent": [],
    })

    def to_dict(self) -> dict:
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

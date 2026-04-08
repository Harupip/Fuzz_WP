from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FuzzableParam:
    location: str
    name: str
    kind: str = "text"
    weight: float = 1.0
    seeds: list[str] = field(default_factory=list)


@dataclass
class CampaignRequest:
    id: str
    method: str
    path: str
    request_weight: float = 1.0
    path_params: dict[str, Any] = field(default_factory=dict)
    query_params: dict[str, Any] = field(default_factory=dict)
    body_params: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    required_state: list[str] = field(default_factory=list)
    ensures_state: dict[str, str] = field(default_factory=dict)
    clears_state: list[str] = field(default_factory=list)
    fuzzable_params: list[FuzzableParam] = field(default_factory=list)


@dataclass
class Campaign:
    schema_version: str
    name: str
    target_name: str
    target_template: str
    request_timeout: int
    default_headers: dict[str, str]
    stop_conditions: dict[str, int]
    summary_path: str
    state_providers: dict[str, str]
    requests: list[CampaignRequest]

    def request_by_id(self, request_id: str) -> CampaignRequest:
        for request in self.requests:
            if request.id == request_id:
                return request
        raise KeyError(f"Unknown request id: {request_id}")


@dataclass
class Candidate:
    candidate_id: str
    request_id: str
    method: str
    path: str
    request_weight: float
    path_params: dict[str, Any]
    query_params: dict[str, Any]
    body_params: dict[str, Any]
    headers: dict[str, str]
    required_state: list[str]
    ensures_state: dict[str, str]
    clears_state: list[str]
    fuzzable_params: list[FuzzableParam]
    parent_id: str | None = None
    mutated_field: str | None = None
    mutation_description: str | None = None
    request_hash: str = ""
    score: int = 1
    priority: int = 1
    energy: int = 1
    coverage_delta: int = 0
    response_status: int | None = None
    response_payload: Any = None
    artifact_path: str | None = None
    interesting_reasons: list[str] = field(default_factory=list)
    executed_callback_ids: list[str] = field(default_factory=list)
    new_callback_ids: list[str] = field(default_factory=list)
    blindspot_callback_ids: list[str] = field(default_factory=list)
    new_hook_names: list[str] = field(default_factory=list)

    def to_summary(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "request_id": self.request_id,
            "parent_id": self.parent_id,
            "mutated_field": self.mutated_field,
            "mutation_description": self.mutation_description,
            "request_hash": self.request_hash,
            "score": self.score,
            "priority": self.priority,
            "energy": self.energy,
            "coverage_delta": self.coverage_delta,
            "response_status": self.response_status,
            "interesting_reasons": self.interesting_reasons,
            "new_callback_ids": self.new_callback_ids,
            "blindspot_callback_ids": self.blindspot_callback_ids,
            "new_hook_names": self.new_hook_names,
        }

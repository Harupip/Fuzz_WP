from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from energy import EnergyScheduler
from energy.request_store import read_request_file

from .campaign import load_campaign
from .models import Campaign, CampaignRequest, Candidate
from .mutator import ShopDemoMutator


class ShopDemoFuzzer:
    def __init__(
        self,
        campaign_path: str,
        target_template: str | None = None,
        max_requests: int | None = None,
        stagnation_limit: int | None = None,
        reset_output: bool = False,
    ):
        self.repo_root = Path(__file__).resolve().parents[3]
        self.output_dir = self.repo_root / "output"
        self.requests_dir = self.output_dir / "requests"
        self.campaign_path = campaign_path
        self.campaign = self.load_campaign()
        if target_template:
            self.campaign.target_template = target_template
        if max_requests is not None:
            self.campaign.stop_conditions["max_requests"] = max_requests
        if stagnation_limit is not None:
            self.campaign.stop_conditions["max_iterations_without_new_coverage"] = stagnation_limit

        self.summary_path = self.repo_root / self.campaign.summary_path
        if reset_output:
            self.reset_output()

        self.requests_dir.mkdir(parents=True, exist_ok=True)
        self.scheduler = EnergyScheduler(
            requests_dir=str(self.requests_dir),
            snapshot_path=str(self.output_dir / "energy_state.json"),
            snapshot_interval=5,
        )
        self.scheduler.load_previous_state()

        self.runtime_state: dict[str, Any] = {}
        self.pending_candidates: list[Candidate] = []
        self.executed_candidates: list[Candidate] = []
        self.seen_request_hashes: set[str] = set()
        self.mutator = ShopDemoMutator()
        self.stagnation_count = 0
        self.session_id = time.strftime("%Y%m%d-%H%M%S")
        self.endpoint_stats: dict[str, dict[str, Any]] = {}
        self._global_new_callbacks: set[str] = set()
        self._global_blindspots: set[str] = set()

    def load_campaign(self) -> Campaign:
        return load_campaign(self.campaign_path)

    def reset_output(self) -> None:
        self.requests_dir.mkdir(parents=True, exist_ok=True)
        for item in self.requests_dir.glob("*.json"):
            item.unlink()
        for artifact_name in (
            "energy_state.json",
            "energy_state.json.processed_ids.json",
            "total_coverage.json",
            "fuzz_summary.json",
        ):
            artifact = self.output_dir / artifact_name
            if artifact.exists():
                artifact.unlink()

    def _new_candidate_id(self) -> str:
        return f"cand-{uuid.uuid4().hex[:10]}"

    def _candidate_hash(
        self,
        request_id: str,
        method: str,
        path: str,
        path_params: dict[str, Any],
        query_params: dict[str, Any],
        body_params: dict[str, Any],
    ) -> str:
        payload = {
            "request_id": request_id,
            "method": method,
            "path": path,
            "path_params": path_params,
            "query_params": query_params,
            "body_params": body_params,
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)

    def _build_candidate(
        self,
        step: CampaignRequest,
        *,
        parent_id: str | None = None,
        mutated_field: str | None = None,
        mutation_description: str | None = None,
        path_params: dict[str, Any] | None = None,
        query_params: dict[str, Any] | None = None,
        body_params: dict[str, Any] | None = None,
    ) -> Candidate:
        next_path = dict(step.path_params if path_params is None else path_params)
        next_query = dict(step.query_params if query_params is None else query_params)
        next_body = dict(step.body_params if body_params is None else body_params)
        return Candidate(
            candidate_id=self._new_candidate_id(),
            request_id=step.id,
            method=step.method,
            path=step.path,
            request_weight=step.request_weight,
            path_params=next_path,
            query_params=next_query,
            body_params=next_body,
            headers={**self.campaign.default_headers, **step.headers},
            required_state=list(step.required_state),
            ensures_state=dict(step.ensures_state),
            clears_state=list(step.clears_state),
            fuzzable_params=list(step.fuzzable_params),
            parent_id=parent_id,
            mutated_field=mutated_field,
            mutation_description=mutation_description,
            request_hash=self._candidate_hash(
                step.id,
                step.method,
                step.path,
                next_path,
                next_query,
                next_body,
            ),
            priority=max(1, int(step.request_weight * 10)),
        )

    def generate_initial_candidates(self) -> list[Candidate]:
        initial = [self._build_candidate(step) for step in self.campaign.requests]
        self.pending_candidates = initial[:]
        return initial

    def _resolve_value(self, value: Any) -> Any:
        if isinstance(value, str) and value.startswith("$state."):
            return self.runtime_state.get(value.split(".", 1)[1])
        return value

    def _resolve_map(self, values: dict[str, Any]) -> dict[str, Any]:
        return {key: self._resolve_value(value) for key, value in values.items()}

    def _extract_response_field(self, payload: Any, dotted_path: str) -> Any:
        current = payload
        for part in dotted_path.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    def _ensure_state(self, state_key: str) -> None:
        if self.runtime_state.get(state_key) not in (None, ""):
            return
        provider_id = self.campaign.state_providers.get(state_key)
        if not provider_id:
            raise RuntimeError(f"No provider configured for state key: {state_key}")
        provider_step = self.campaign.request_by_id(provider_id)
        provider_candidate = self._build_candidate(provider_step)
        self.execute_candidate(provider_candidate, is_setup=True)
        if self.runtime_state.get(state_key) in (None, ""):
            raise RuntimeError(f"State provider {provider_id} did not populate {state_key}")

    def _render_candidate(self, candidate: Candidate) -> tuple[str, dict[str, str], bytes | None]:
        for state_key in candidate.required_state:
            self._ensure_state(state_key)

        path_params = self._resolve_map(candidate.path_params)
        query_params = self._resolve_map(candidate.query_params)
        body_params = self._resolve_map(candidate.body_params)

        rendered_path = candidate.path.format(**path_params)
        url = self.campaign.target_template.format(path=rendered_path)
        if query_params:
            separator = "&" if parse.urlparse(url).query else "?"
            url = url + separator + parse.urlencode(query_params)

        headers = dict(candidate.headers)
        headers["X-UOPZ-FUZZ-ID"] = candidate.candidate_id
        data = None
        if body_params and candidate.method != "GET":
            data = parse.urlencode(body_params).encode("utf-8")
        return url, headers, data

    def _send_request(self, candidate: Candidate) -> tuple[int, Any]:
        url, headers, data = self._render_candidate(candidate)
        req = request.Request(url=url, data=data, method=candidate.method)
        for key, value in headers.items():
            req.add_header(key, value)

        try:
            with request.urlopen(req, timeout=self.campaign.request_timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
                status = response.status
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            status = exc.code
        except Exception as exc:  # pragma: no cover
            return 0, {"error": str(exc)}

        try:
            return status, json.loads(raw)
        except json.JSONDecodeError:
            return status, {"raw": raw}

    def _match_fuzz_id(self, payload: dict[str, Any], fuzz_id: str) -> bool:
        headers = payload.get("request_params", {}).get("headers", {})
        if not isinstance(headers, dict):
            return False
        for key, value in headers.items():
            if str(key).lower() == "x-uopz-fuzz-id" and str(value) == fuzz_id:
                return True
        return False

    def _wait_for_artifact(self, seen_files: set[str], fuzz_id: str) -> str | None:
        deadline = time.time() + self.campaign.request_timeout + 2
        fallback_path = None
        while time.time() < deadline:
            current_files = {str(path) for path in self.requests_dir.glob("*.json")}
            new_files = sorted(current_files - seen_files)
            for file_path in new_files:
                payload = read_request_file(file_path)
                if not isinstance(payload, dict):
                    continue
                fallback_path = file_path
                if self._match_fuzz_id(payload, fuzz_id):
                    return file_path
            time.sleep(0.25)
        return fallback_path

    def _record_endpoint_stats(self, candidate: Candidate) -> None:
        stats = self.endpoint_stats.setdefault(candidate.request_id, {
            "requests": 0,
            "best_score": 0,
            "new_callbacks": 0,
            "blindspot_hits": 0,
        })
        stats["requests"] += 1
        stats["best_score"] = max(stats["best_score"], candidate.score)
        stats["new_callbacks"] += len(candidate.new_callback_ids)
        stats["blindspot_hits"] += len(candidate.blindspot_callback_ids)

    def _calculate_priority(self, result) -> int:
        return (
            len(result.new_callback_ids) * 100
            + len(result.new_hook_names) * 50
            + len(result.blindspot_callback_ids) * 25
            + len(result.rare_callback_ids) * 10
            + max(1, result.score)
        )

    def _assign_feedback(self, candidate: Candidate, result) -> None:
        candidate.score = result.score
        candidate.coverage_delta = result.coverage_delta
        candidate.energy = max(1, min(result.score, 6))
        candidate.priority = self._calculate_priority(result)
        candidate.executed_callback_ids = list(result.executed_callback_ids)
        candidate.new_callback_ids = list(result.new_callback_ids)
        candidate.blindspot_callback_ids = list(result.blindspot_callback_ids)
        candidate.new_hook_names = list(result.new_hook_names)
        reasons = []
        if result.new_callback_ids:
            reasons.append("new_callback")
        if result.new_hook_names:
            reasons.append("new_hook")
        if result.blindspot_callback_ids:
            reasons.append("blindspot")
        if result.rare_callback_ids:
            reasons.append("rare_callback")
        candidate.interesting_reasons = reasons

    def execute_candidate(self, candidate: Candidate, *, is_setup: bool = False) -> Candidate:
        seen_files = {str(path) for path in self.requests_dir.glob("*.json")}
        status, payload = self._send_request(candidate)
        candidate.response_status = status
        candidate.response_payload = payload

        artifact_path = self._wait_for_artifact(seen_files, candidate.candidate_id)
        candidate.artifact_path = artifact_path
        if artifact_path:
            result = self.scheduler.process_request_file(artifact_path)
            if result is not None:
                self._assign_feedback(candidate, result)
                self._global_new_callbacks.update(candidate.new_callback_ids)
                self._global_blindspots.update(candidate.blindspot_callback_ids)
                if candidate.new_callback_ids or candidate.new_hook_names:
                    self.stagnation_count = 0
                else:
                    self.stagnation_count += 1

        if isinstance(payload, dict):
            for state_key, response_path in candidate.ensures_state.items():
                extracted = self._extract_response_field(payload, response_path)
                if extracted not in (None, ""):
                    self.runtime_state[state_key] = extracted
            if status and status < 400:
                for state_key in candidate.clears_state:
                    self.runtime_state.pop(state_key, None)

        self._record_endpoint_stats(candidate)
        if not is_setup:
            self.executed_candidates.append(candidate)
        return candidate

    def _spawn_mutations(self, candidate: Candidate) -> list[Candidate]:
        request_def = self.campaign.request_by_id(candidate.request_id)
        children: list[Candidate] = []
        for fuzzable in candidate.fuzzable_params:
            current_map = {
                "path": candidate.path_params,
                "query": candidate.query_params,
                "body": candidate.body_params,
            }[fuzzable.location]
            variants = self.mutator.mutate_value(current_map.get(fuzzable.name), fuzzable.kind, fuzzable.seeds)
            for variant in variants:
                next_map = dict(current_map)
                next_map[fuzzable.name] = variant
                child = self._build_candidate(
                    request_def,
                    parent_id=candidate.candidate_id,
                    mutated_field=f"{fuzzable.location}:{fuzzable.name}",
                    mutation_description=f"{fuzzable.name} -> {variant}",
                    path_params=next_map if fuzzable.location == "path" else candidate.path_params,
                    query_params=next_map if fuzzable.location == "query" else candidate.query_params,
                    body_params=next_map if fuzzable.location == "body" else candidate.body_params,
                )
                if child.request_hash in self.seen_request_hashes:
                    continue
                child.priority = max(1, candidate.priority + candidate.energy)
                children.append(child)
        return children

    def schedule_next_candidate(self) -> Candidate | None:
        if not self.pending_candidates:
            return None
        self.pending_candidates.sort(
            key=lambda item: (item.priority, item.score, item.request_weight, item.candidate_id),
            reverse=True,
        )
        return self.pending_candidates.pop(0)

    def _build_summary(self, stop_reason: str) -> dict[str, Any]:
        top_candidates = sorted(
            self.executed_candidates,
            key=lambda item: (item.score, item.priority, item.coverage_delta),
            reverse=True,
        )[:10]
        return {
            "schema_version": "uopz-fuzz-session-v1",
            "session_id": self.session_id,
            "campaign": self.campaign.name,
            "target_name": self.campaign.target_name,
            "target_template": self.campaign.target_template,
            "stop_reason": stop_reason,
            "requests_sent": len(self.executed_candidates),
            "unique_candidates": len(self.seen_request_hashes),
            "runtime_state": self.runtime_state,
            "new_callbacks_discovered": sorted(self._global_new_callbacks),
            "blindspots_touched": sorted(self._global_blindspots),
            "endpoint_stats": self.endpoint_stats,
            "top_candidates": [candidate.to_summary() for candidate in top_candidates],
        }

    def run(self) -> dict[str, Any]:
        if not self.pending_candidates:
            self.generate_initial_candidates()

        max_requests = int(self.campaign.stop_conditions.get("max_requests", 40))
        stagnation_limit = int(self.campaign.stop_conditions.get("max_iterations_without_new_coverage", 10))
        stop_reason = "queue_exhausted"

        while len(self.executed_candidates) < max_requests:
            candidate = self.schedule_next_candidate()
            if candidate is None:
                stop_reason = "queue_exhausted"
                break
            if candidate.request_hash in self.seen_request_hashes:
                continue

            self.seen_request_hashes.add(candidate.request_hash)
            executed = self.execute_candidate(candidate)
            self.pending_candidates.extend(self._spawn_mutations(executed))

            if self.stagnation_count >= stagnation_limit:
                stop_reason = "stagnation_limit"
                break
        else:
            stop_reason = "max_requests"

        summary = self._build_summary(stop_reason)
        self.summary_path.parent.mkdir(parents=True, exist_ok=True)
        self.summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        self.scheduler.save_state()
        return summary

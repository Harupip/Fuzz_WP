from __future__ import annotations

import json
from pathlib import Path

from .models import Campaign, CampaignRequest, FuzzableParam


def load_campaign(campaign_path: str) -> Campaign:
    payload = json.loads(Path(campaign_path).read_text(encoding="utf-8"))
    requests = []
    for item in payload.get("requests", []):
        fuzzable = [
            FuzzableParam(
                location=entry["location"],
                name=entry["name"],
                kind=entry.get("kind", "text"),
                weight=float(entry.get("weight", 1.0)),
                seeds=[str(seed) for seed in entry.get("seeds", [])],
            )
            for entry in item.get("fuzzable_params", [])
        ]
        requests.append(
            CampaignRequest(
                id=item["id"],
                method=item["method"].upper(),
                path=item["path"],
                request_weight=float(item.get("request_weight", 1.0)),
                path_params=dict(item.get("path_params", {})),
                query_params=dict(item.get("query_params", {})),
                body_params=dict(item.get("body_params", {})),
                headers=dict(item.get("headers", {})),
                required_state=list(item.get("required_state", [])),
                ensures_state=dict(item.get("ensures_state", {})),
                clears_state=list(item.get("clears_state", [])),
                fuzzable_params=fuzzable,
            )
        )

    return Campaign(
        schema_version=payload.get("schema_version", "uopz-campaign-v1"),
        name=payload["name"],
        target_name=payload["target_name"],
        target_template=payload["target_template"],
        request_timeout=int(payload.get("request_timeout", 5)),
        default_headers=dict(payload.get("default_headers", {})),
        stop_conditions=dict(payload.get("stop_conditions", {})),
        summary_path=payload.get("summary_path", "output/fuzz_summary.json"),
        state_providers=dict(payload.get("state_providers", {})),
        requests=requests,
    )

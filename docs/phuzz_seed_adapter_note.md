# PHUZZ Seed Adapter Note

## Purpose

This note describes the output contracts prepared by the current demo for future PHUZZ integration.
It does not integrate directly into PHUZZ yet.

## Output Files

### `output/hook_gap_report.json`

Primary purpose:
- callback-level coverage comparison

Useful fields for a future adapter:
- `callback_id`
- `hook_name`
- `callback_name`
- `callback_type`
- `priority`
- `accepted_args`
- `source_file`
- `source_line`
- `is_active`
- `register_count`
- `execute_count`
- `status`
- `seed_priority`
- `target_family`
- `generation_status`
- `notes`

### `output/suggested_seeds.json`

Primary purpose:
- uncovered callback candidates prepared for replay or later fuzzing seed import

Useful fields for a future adapter:
- `hook_name`
- `callback_id`
- `callback_name`
- `seed_priority`
- `priority_rank`
- `direct_http_supported`
- `generation_status`
- `seed.method`
- `seed.path`
- `seed.content_type`
- `seed.body`
- `seed.auth_mode`

### `output/suggested_seeds.md`

Primary purpose:
- human-readable review only

PHUZZ should not rely on this file as a machine contract.

## Stability Intent

The current demo keeps the following meanings stable on purpose:

- `status`
  - `covered` means the callback has aggregate runtime execution count > 0
  - `uncovered` means the callback is registered in aggregate runtime data but still has execution count 0

- `seed_priority`
  - seed-specific prioritization only
  - not a replacement for existing energy logic

- `generation_status`
  - explains whether a direct HTTP seed was generated or manual analysis is still required

- `direct_http_supported`
  - `true` only when the hook name maps directly to a known WordPress entry point

## Demo-Specific Parts

The following details are demo-specific and should be treated as provisional:

- additive `shop-demo` callback names used for validation
- default replay base URL
- current markdown formatting in `suggested_seeds.md`
- simple heuristics for medium/low seed priority

## Recommended Future PHUZZ Use

The most direct future adapter path is:

1. Read `output/suggested_seeds.json`
2. Keep only entries where:
   - `status == "uncovered"`
   - `is_active == true`
3. Split into:
   - direct HTTP seeds
   - manual-analysis queue
4. Convert direct HTTP seeds into PHUZZ candidate requests
5. Preserve `hook_name`, `callback_id`, and `seed_priority` as tracking metadata

## Scope Boundary

This adapter preparation does not:
- replace current energy scoring
- mutate or schedule requests
- infer missing auth, nonce, or workflow context
- generate fake HTTP requests for unsupported hooks

Those richer steps are intentionally left for later PHUZZ integration.

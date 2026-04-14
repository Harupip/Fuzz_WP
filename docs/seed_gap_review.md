# Seed Gap Review for Existing UOPZ Demo

## Review Scope

This note reviews the current UOPZ hook demo before adding seed-generation logic.
The goal is to reuse the existing runtime collection and reporting path, and only add the missing seed-focused pipeline.

## Relevant Existing Files

### `fuzzer-core/uopz_hook_v2.php`

What it already does:
- Tracks hook registration via `add_action` and `add_filter`.
- Tracks unregister events via `remove_action`, `remove_filter`, `remove_all_actions`, and `remove_all_filters`.
- Tracks actual callback execution and does not rely only on registration snapshots.
- Detects endpoint styles including:
  - `REST:/...`
  - `ADMIN_AJAX:<action>`
  - `ADMIN_POST:<action>`
- Exports per-request artifacts to `output/requests/*.json`.
- Exports aggregate callback coverage to `output/total_coverage.json`.
- Exports aggregate hook/emitter registry to `output/hook_registry.json`.

What can be reused unchanged:
- Callback-level `registered_callbacks`
- Callback-level `executed_callbacks`
- Callback-level `blindspot_callbacks`
- Endpoint detection for `admin-ajax.php` and `admin-post.php`
- `hook_registry` aggregate structure for hook/emitter metadata

What should not be touched:
- Existing runtime instrumentation and export schema, because the current PHP side already provides enough data for seed generation.
- This file is also currently dirty in the worktree, so changing it would add avoidable risk.

### `output/total_coverage.json`

What it already does:
- Provides aggregate callback-level coverage data across requests.
- Stores both registered and executed callback maps.
- Already computes the equivalent of uncovered callbacks through `blindspot_callbacks`.

What can be reused unchanged:
- As the main machine-readable source for uncovered callback extraction.
- As a stable source for callback metadata such as:
  - `hook_name`
  - `callback_repr`
  - `type`
  - `priority`
  - `accepted_args`
  - `source_file`
  - `source_line`
  - `is_active`
  - `status`

### `output/hook_registry.json`

What it already does:
- Organizes data by hook and emitter.
- Shows which hooks are fired and which callbacks are attached.
- Preserves useful runtime metadata such as hook fire count and emitter source locations.

What can be reused unchanged:
- As supporting metadata for human-readable reporting.
- As a future bridge for PHUZZ-facing enrichment.

What is not yet enough by itself:
- It does not generate seed requests.
- It does not rank uncovered callbacks for seed generation.

### `fuzzer-core/hook_energy_demo/collector.py`

What it already does:
- Reads per-request artifacts safely.
- Normalizes callback identity.
- Merges callback registry into Python state.
- Builds request observations from runtime JSON.

What can be reused indirectly:
- Identity normalization strategy
- Request artifact reading flow
- Existing separation of collector vs calculator vs reporter

What should be extended:
- Prefer adding seed-specific logic in new files instead of expanding this collector directly, because the existing collector is focused on request-scoring for hook energy.

### `fuzzer-core/hook_energy_demo/models.py`

What it already does:
- Defines stable Python-side callback descriptors and per-request execution models.
- Preserves fields useful for reporting and future adapters.

What can be reused indirectly:
- Naming style for callback metadata
- State/report structure conventions
- Existing JSON export style

### `fuzzer-core/hook_energy_demo/reporter.py`

What it already does:
- Writes human-readable energy summaries.
- Writes JSON summaries for the energy demo.
- Produces rankings for rare and never-executed callbacks.

What can be reused indirectly:
- File organization and summary-writing conventions
- Ranking/report formatting style

What is missing for seed generation:
- No callback gap report dedicated to seed generation
- No seed-priority ranking
- No HTTP seed templates

### `fuzzer-core/hook_energy_demo/state.py`

What it already does:
- Persists callback registry and processed request ids across runs.

What can be reused indirectly:
- State snapshot conventions and JSON persistence style

What is missing for seed generation:
- No dedicated seed-analysis state is currently needed, because seed generation can derive from aggregate runtime outputs instead of maintaining a new long-lived energy-like state.

### `fuzzer-core/hook_energy_demo/cli.py`

What it already does:
- Processes pending request artifacts for hook energy scoring.
- Saves state and summary outputs.

What can be reused indirectly:
- CLI layout and output-directory defaults

What should be extended:
- Prefer adding a separate seed CLI instead of complicating the current energy CLI.

### `target-app/shop-demo/shop-demo.php`

What it already does:
- Registers the current demo plugin hooks.
- Exposes REST endpoints for product/order CRUD and hook lab.
- Includes blindspot/internal hooks:
  - `shop_secret_admin_export`
  - `shop_process_refund`
  - `shop_send_invoice_email`
- Includes a manual trigger flow via REST and browser UI for the current demo routes.

What can be reused unchanged:
- Existing REST-based demo scenarios
- Existing internal blindspot hooks for unsupported-seed reporting
- Existing hook-lab behavior for remove/covered demonstrations unrelated to seed generation

What is missing:
- No `wp_ajax_*` callbacks
- No `wp_ajax_nopriv_*` callbacks
- No `admin_post_*` callbacks
- No `admin_post_nopriv_*` callbacks
- No direct replay target for generated WordPress entry-point seeds

### `fuzzer-core/fuzzing/campaigns/shop_demo_v1.json`

What it already does:
- Defines the current request seeds for the prototype fuzzer.
- Shows how request data is represented for later automation.

What can be reused indirectly:
- Request structure and field naming conventions
- Target-template expectations

What is missing:
- No automatic conversion from uncovered callbacks into new seed requests.

## Answers to the Required Review Questions

### 1. What is already implemented?

Hook registration tracking:
- Already implemented in PHP runtime export.

Hook execution tracking:
- Already implemented in PHP runtime export at callback level.

Callback normalization:
- Already implemented in both PHP export fields and Python `HookCollector`.

Report generation:
- Already implemented for coverage aggregates and hook-energy summaries.

Demo plugin behavior:
- Already implemented for REST routes and internal blindspot hooks.

Request replay or manual trigger flow:
- Already exists for REST-based demo paths and current fuzz campaign execution.
- Does not yet exist for generated `admin-ajax.php` or `admin-post.php` seeds.

### 2. What exists inside `fuzzer-core/hook_energy_demo` that can be reused indirectly?

Report structures:
- Existing summary/report writing patterns

Scoring fields:
- Existing callback metadata and ranking conventions can be mirrored, but energy scoring itself must not be reused or redesigned for seeds

Hook metadata:
- Existing callback descriptor field names and JSON style

File organization:
- Clean separation by purpose (`collector`, `calculator`, `reporter`, `state`, `cli`)

Logging format:
- Existing human-readable summary style and JSON outputs

### 3. Which parts are missing specifically for seed generation?

Missing pieces:
- A dedicated uncovered-callback report for seed generation
- Seed-priority ranking separate from hook energy
- WordPress entry-point hook classification logic
- Seed template generation for:
  - `wp_ajax_*`
  - `wp_ajax_nopriv_*`
  - `admin_post_*`
  - `admin_post_nopriv_*`
- Replay support for generated seeds
- Demo callbacks using those WordPress entry-point hooks
- Seed-specific docs and PHUZZ adapter note

## What Should Be Reused Unchanged

- `fuzzer-core/uopz_hook_v2.php`
- Aggregate runtime outputs:
  - `output/total_coverage.json`
  - `output/hook_registry.json`
- Existing `hook_energy_demo` energy logic
- Existing fuzzing energy modules in `fuzzer-core/fuzzing/energy/`

## What Should Be Extended

- Add a seed-focused Python pipeline under `fuzzer-core/hook_energy_demo/`
- Add additive WordPress entry-point demo callbacks in `target-app/shop-demo/shop-demo.php`
- Add tests and docs for seed generation and replay

## What Must Not Be Reimplemented

- Hook energy logic
- Runtime instrumentation for registration/execution tracking
- Existing aggregate coverage math already produced by PHP

## Minimal Implementation Direction

Recommended low-risk additions:

1. Add a standalone seed-analysis module that reads:
   - `output/total_coverage.json`
   - `output/hook_registry.json`

2. Generate:
   - `output/hook_gap_report.json`
   - `output/suggested_seeds.json`
   - optional human-readable markdown output

3. Add demo callbacks for WordPress entry-point hooks in `shop-demo` so the seed pipeline has realistic uncovered targets to rank and replay.

4. Add a replay helper that can manually execute generated seeds and support before/after coverage verification.

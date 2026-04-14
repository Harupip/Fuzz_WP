# Hook Seed Demo Guide

## Goal

This guide explains how to:
- collect runtime hook data from the existing UOPZ demo
- generate uncovered-callback and suggested-seed outputs
- replay a generated seed
- verify that a callback moves from uncovered to covered

## What Changed

The demo now has additive WordPress entry-point callbacks for:
- `wp_ajax_shop_demo_refresh_panel`
- `wp_ajax_nopriv_shop_demo_public_ping`
- `admin_post_shop_demo_export_orders`
- `admin_post_nopriv_shop_demo_public_export`

These callbacks exist only to validate the seed-generation pipeline on top of the current demo.

## Step 1. Start the Existing Environment

Use the same environment as the current UOPZ demo:

```powershell
docker compose up -d --build
```

## Step 2. Trigger Normal Demo Traffic

You can use the existing UI or the current REST flows to generate baseline request artifacts.

Examples already present in the demo:
- `POST /wp-json/shop/v1/products`
- `POST /wp-json/shop/v1/orders`
- `POST /wp-json/shop/v1/hooks/lab`

The runtime artifacts will continue to appear in:
- `output/requests/`
- `output/total_coverage.json`
- `output/hook_registry.json`

## Step 3. Generate Uncovered Callback and Seed Outputs

Run the new seed CLI:

```powershell
python fuzzer-core/hook_energy_demo/seed_cli.py
```

This writes:
- `output/hook_gap_report.json`
- `output/suggested_seeds.json`
- `output/suggested_seeds.md`

## Step 4. Inspect the Outputs

### `output/hook_gap_report.json`

Contains callback-level coverage comparison with fields such as:
- `hook_name`
- `callback_name`
- `register_count`
- `execute_count`
- `status`
- `seed_priority`
- `generation_status`

### `output/suggested_seeds.json`

Contains the seed-focused uncovered list.

For direct WordPress entry-point hooks, the file contains a minimal HTTP seed.
For internal hooks, the file keeps a note and does not invent a fake HTTP request.

## Step 5. Demo Scenario A: Uncovered AJAX Callback

Before replay, generate the report and confirm that:
- `wp_ajax_nopriv_shop_demo_public_ping` appears as `uncovered`
- a seed exists for `/wp-admin/admin-ajax.php`

You should see a seed similar to:

```json
{
  "hook_name": "wp_ajax_nopriv_shop_demo_public_ping",
  "seed_priority": "highest",
  "seed": {
    "method": "POST",
    "path": "/wp-admin/admin-ajax.php",
    "content_type": "application/x-www-form-urlencoded",
    "body": {
      "action": "shop_demo_public_ping"
    }
  }
}
```

## Step 6. Demo Scenario B: Replay Generated AJAX Seed

Replay the generated seed and verify coverage after replay:

```powershell
python fuzzer-core/hook_energy_demo/seed_cli.py `
  --replay-hook wp_ajax_nopriv_shop_demo_public_ping `
  --verify-after-replay
```

Expected result:
- the request is sent to `/wp-admin/admin-ajax.php`
- aggregate coverage updates
- the replay result reports `covered_after_replay: true`

Then run the generator again:

```powershell
python fuzzer-core/hook_energy_demo/seed_cli.py
```

Now the callback should no longer appear as uncovered.

## Step 7. Demo Scenario C: Replay Generated Admin-Post Seed

Use the unauth-capable admin-post demo hook:

```powershell
python fuzzer-core/hook_energy_demo/seed_cli.py `
  --replay-hook admin_post_nopriv_shop_demo_public_export `
  --verify-after-replay
```

Expected result:
- the request is sent to `/wp-admin/admin-post.php`
- aggregate coverage updates
- the callback becomes covered

## Step 8. Demo Scenario D: Internal Hook Remains Manual-Only

Internal hooks such as:
- `shop_process_refund`
- `shop_secret_admin_export`
- `shop_send_invoice_email`

may still appear uncovered, but the seed output should not create fake HTTP requests for them.
Instead, they remain marked as manual or later-analysis targets.

## Notes About Authenticated Hooks

The demo also registers:
- `wp_ajax_shop_demo_refresh_panel`
- `admin_post_shop_demo_export_orders`

These are valid highest-priority seed targets, but replaying them requires an authenticated WordPress session.
For simple validation, prefer the `nopriv` hooks first.

## Expected Output Files

- `docs/seed_gap_review.md`
- `output/hook_gap_report.json`
- `output/suggested_seeds.json`
- `output/suggested_seeds.md`
- `docs/phuzz_seed_adapter_note.md`

## Vietnamese Note

Important code comments inside the implementation are intentionally written in Vietnamese, as requested for the seed-generation pipeline stage.

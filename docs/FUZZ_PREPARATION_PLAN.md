# Shop Demo Fuzz Preparation

## Muc tieu

Tai lieu nay chot bo khung da duoc implement de chuan bi fuzz cho `shop-demo` theo huong cua `PHUZZ`:

- co campaign config rieng cho `shop-demo`
- co Python orchestrator de load seed, gui request, doc artifact, tinh energy, va mutate tiep
- per-request artifact da giu du callback-level data de scheduler dung duoc cho blindspot/newness
- scheduler da persist `processed_ids` de restart khong reprocess request cu

## Thanh phan moi

- `fuzzer-core/fuzzing/campaigns/shop_demo_v1.json`
  Campaign v1 bao phu toan bo surface hien co cua plugin:
  `GET /products`, `POST /products`, `GET /products/{id}`, `PUT /products/{id}`, `DELETE /products/{id}`, `GET /orders`, `POST /orders`, `POST /hooks/lab`.
- `fuzzer-core/fuzzing/orchestrator/`
  Package moi cho orchestrator fuzz:
  `load_campaign()`, `generate_initial_candidates()`, `execute_candidate()`, `schedule_next_candidate()`.
- `fuzzer-core/fuzzing/cli_fuzz.py`
  CLI de chay session fuzz v1 tu host.
- `output/fuzz_summary.json`
  Session summary gom top candidate, callback moi, blindspot da cham, va endpoint stats.

## Feedback Artifact

`fuzzer-core/uopz_hook_v2.php` da duoc mo rong de per-request artifact giu:

- `schema_version`
- `hook_coverage.registered_callbacks`
- `hook_coverage.executed_callbacks`
- `hook_coverage.blindspot_callbacks`
- `executed_callback_ids`
- `blindspot_callback_ids`
- `new_callback_ids`
- `rare_callback_ids`
- `frequent_callback_ids`
- `new_hook_names`
- `coverage_delta`
- `score`

Moi callback entry hien co them:

- `stable_id`
- `runtime_id`
- `callback_runtime_id`
- `source_file`
- `source_line`

`EnergyScheduler` se enrich request artifact sau khi process de ghi lai score va callback feedback vao chinh file request.

## Quy trinh chay v1

### 1. Khoi dong runtime

```powershell
docker compose up -d --build
```

### 2. Reset artifact truoc session moi

```powershell
python fuzzer-core/fuzzing/cli_fuzz.py --reset-output --max-requests 40 --stagnation-limit 10
```

Flag `--reset-output` se xoa:

- `output/requests/*.json`
- `output/energy_state.json`
- `output/energy_state.json.processed_ids.json`
- `output/total_coverage.json`
- `output/fuzz_summary.json`

### 3. Theo doi energy neu can

```powershell
python fuzzer-core/fuzzing/energy/cli_watch.py
```

### 4. Session output can kiem tra

- `output/requests/`
  Raw + enriched per-request artifacts
- `output/total_coverage.json`
  Aggregate coverage do PHP runtime merge
- `output/energy_state.json`
  Snapshot aggregate state cua Python scheduler
- `output/fuzz_summary.json`
  Tong ket session fuzz v1

## Tieu chi dung session v1

Mac dinh campaign hien dung:

- `max_requests = 40`
- `max_iterations_without_new_coverage = 10`

Co the override bang:

```powershell
python fuzzer-core/fuzzing/cli_fuzz.py --max-requests 80 --stagnation-limit 20
```

## Kiem thu co san

Smoke tests local:

```powershell
python -m unittest discover fuzzer-core/fuzzing/tests -v
```

Test hien cover:

- campaign bao phu du 8 endpoint cua `shop-demo`
- initial candidate generation dung theo campaign
- scheduler enrich request artifact va persist `processed_ids`

## Gioi han con lai

- `callback_id` lich su van la key chinh cho energy; `runtime_id` da duoc export de tiep tuc verify edge case closure/object instance.
- Orchestrator v1 la single-node, chua co sync nhieu worker.
- Mutation hien tap trung vao `name`, `description`, `price`, `stock`, `product_id`, `quantity`, `customer`, `scenario`.
- DB reset van khuyen nghi thong qua Docker volume reset neu can mot session sach hoan toan.

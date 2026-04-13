# Hook Coverage Energy Demo

## Muc tieu

Tai lieu nay mo ta ban demo hook-based energy cho `shop-demo`.
Ban demo nay:

- dung du lieu runtime do UOPZ da export
- khong tich hop vao PHUZZ scoring/selection/mutation loop hien tai
- chi tap trung vao callback registry, callback execution, va hook energy de trinh bay concept

## Khao sat hien trang

### File va luong hien co

- `target-app/shop-demo/shop-demo.php`
  - Dang ky callback qua `add_action` / `add_filter`
  - Trigger hook qua `do_action` / `apply_filters`
  - Co route `POST /hooks/lab` de tao runtime callback va test `remove_action` / `remove_filter`
- `fuzzer-core/uopz_hook_v2.php`
  - Theo doi registration cho `add_action`, `add_filter`
  - Theo doi unregister cho `remove_action`, `remove_filter`, `remove_all_actions`, `remove_all_filters`
  - Theo doi hook fire qua `do_action`, `apply_filters`, `*_ref_array`
  - Theo doi callback invocation thuc te qua `call_user_func`, `call_user_func_array`
  - Ghi per-request artifact vao `output/requests/*.json`
  - Ghi aggregate coverage vao `output/total_coverage.json`
  - Ban worktree hien tai con bo sung `hook_registry` de tong hop emitter/hook/callback theo request
- `fuzzer-core/fuzzing/energy/`
  - Dang co energy logic theo tier/bonus/max clamp
  - Hanh vi nay phu hop cho fuzz prototype, nhung phuc tap hon muc can thiet cho demo hook energy

### Hook trong shop-demo

- `shop_activate`
  - trigger `shop_plugin_activated`
- `shop_get_products`
  - trigger `shop_filter_products_list`
- `shop_get_product`
  - trigger `shop_filter_single_product`
- `shop_create_product`
  - trigger `shop_before_create_product`
  - trigger `shop_product_created`
- `shop_update_product`
  - trigger `shop_before_update_product`
  - trigger `shop_product_updated`
- `shop_delete_product`
  - trigger `shop_before_delete_product`
  - trigger `shop_product_deleted`
- `shop_get_orders`
  - trigger `shop_filter_orders_list`
- `shop_create_order`
  - trigger `shop_calculate_order_total`
  - trigger `shop_order_placed`
- `shop_run_hook_lab`
  - tao callback runtime tren `shop_demo_runtime_action`
  - tao callback runtime tren `shop_demo_runtime_filter`
  - bat/tat listener `all`

## Phan duoc don gian hoa cho demo

### Logic cu khong duoc dung cho demo nay

Phan `fuzzer-core/fuzzing/energy/` hien co dang co:

- tier `first_seen` / `rare` / `frequent`
- `blindspot_bonus`
- `new_hook_bonus`
- `max_energy`
- enrich artifact de phuc vu fuzz loop

Cac thanh phan tren khong duoc dung cho demo standalone vi:

- kho giai thich nhanh trong buoi demo
- da tron logic research/fuzzer vao logic hook energy co ban
- vuot ra khoi boundary "chua tich hop PHUZZ"

### Module moi

Ban demo moi nam o:

- `fuzzer-core/hook_energy_demo/collector.py`
- `fuzzer-core/hook_energy_demo/calculator.py`
- `fuzzer-core/hook_energy_demo/reporter.py`
- `fuzzer-core/hook_energy_demo/state.py`
- `fuzzer-core/hook_energy_demo/cli.py`

Trach nhiem duoc tach ro:

- `HookCollector`
  - doc request artifacts
  - giu registry callback active/removed
  - lay tap callback thuc thi duy nhat cua tung request
  - cap nhat global execution count sau khi request da duoc score
- `HookEnergyCalculator`
  - tinh `hook_score(callback) = 1 / (N + 1)`
  - tinh `hook_energy(request) = max(scores)`
  - tinh them `hook_energy_avg` de debug
- `HookEnergyReporter`
  - in debug summary cho tung request
  - xep hang request co energy cao
  - liet ke callback hiem va callback chua tung execute

## Mo hinh dinh danh callback

Ban demo dung callback identity on dinh theo thong tin da co trong artifact:

- `callback_id`
  - duoc UOPZ tao tu `hook_name + stable callback identity + priority`
- `callback_identity`
  - uu tien `callback_repr`
  - fallback qua `stable_id`
  - fallback qua `runtime_id`
  - cuoi cung moi fallback ve `callback_id`

Gia tri hien thi de debug:

```text
hook_name :: callback_identity :: priority=<priority>
```

## Cong thuc cuoi cung

### Callback score

```text
hook_score(callback) = 1 / (N + 1)
```

Trong do:

- `N` = tong so lan callback da execute truoc request hien tai
- score duoc tinh truoc
- chi sau khi score xong moi cap nhat global execution count

### Request energy

Cong thuc mac dinh:

```text
hook_energy(request) = max(hook_score(callback_i))
```

Secondary metric de debug:

```text
hook_energy_avg(request) = average(hook_score(callback_i))
```

Neu request khong co callback nao duoc track:

```text
hook_energy(request) = 0
```

## Cach chay demo

Xu ly toan bo request artifact chua duoc tinh:

```powershell
python fuzzer-core/hook_energy_demo/cli.py
```

Watch lien tuc de bat request moi:

```powershell
python fuzzer-core/hook_energy_demo/cli.py --watch
```

Artifact moi duoc tao:

- `output/hook_energy_demo_state.json`
  - global execution count va callback registry
- `output/hook_energy_demo_summary.json`
  - request reports cua lan chay hien tai
  - ranking request/callback

## Vi du dien giai

### Callback moi

Neu callback chua tung execute:

```text
N = 0
score = 1 / (0 + 1) = 1.0
```

### Callback cu

Neu callback da execute 3 lan:

```text
N = 3
score = 1 / (3 + 1) = 0.25
```

### Request cham callback hiem

Neu request co:

- callback A: `N=8 => score=0.111111`
- callback B: `N=0 => score=1.0`

Thi:

```text
hook_energy = max(0.111111, 1.0) = 1.0
```

Request nay xung dang duoc uu tien hon vi no cham vao callback moi/hiem.

### Request khong cham callback nao

```text
hook_energy = 0
```

## Phan de lai cho tich hop PHUZZ sau nay

Ban demo nay chu y giu san cac diem noi:

- collector/calculator/reporter da tach rieng
- callback identity va global execution count da duoc chuan hoa
- request report da co `hook_energy` va `hook_energy_avg`

Nhung hien tai co y khong lam:

- khong ket hop voi `Power_PHUZZ`
- khong normalize tren candidate pool
- khong thay doi mutation count
- khong chinh loop selection trong orchestrator hien tai

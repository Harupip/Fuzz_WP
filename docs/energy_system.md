# Energy-Based Scheduling System

## Tong quan

Energy quyet dinh request/candidate nao dang xung dang duoc mutate nhieu hon. Score cao hon nghia la request vua mo them callback moi, cham vao blindspot, hoac kich hoat hook hiem.

Flow hien tai:

```text
PHP runtime -> per-request JSON -> Python EnergyScheduler -> energy_state.json / mutation policy
```

## Luong du lieu

1. PHP side ghi raw request artifact vao `output/requests/`
2. Python side doc cac file moi
3. `EnergyCalculator` tinh diem dua tren executed callbacks va lich su aggregate
4. `GlobalCoverageState` cap nhat histogram, seen hooks, va blindspots
5. Snapshot rieng cua Python duoc ghi ra `output/energy_state.json`

Luu y:

- `output/total_coverage.json` la aggregate coverage do PHP runtime merge tren moi request
- `output/energy_state.json` la state rieng cua Python energy watcher

## Inputs quan trong

Tu per-request JSON, energy layer su dung chu yeu:

- `hook_coverage.executed_callbacks`
- `hook_coverage_summary`
- metadata nhu `request_id`, `endpoint`, `input_signature`

Moi entry trong `hook_coverage.executed_callbacks` hien chi giu:

- `callback_id`
- `hook_name`
- `callback_repr`
- `executed_count`

## Tier classification

Moi callback duoc xep hang dua tren historical execution count:

| Historical count | Tier | Default weight |
|---|---|---|
| `0` | `first_seen` | `12` |
| `1..3` | `rare` | `5` |
| `>3` | `frequent` | `1` |

## Bonuses

| Bonus | Default | Dieu kien |
|---|---|---|
| `blindspot_bonus` | `8` | Callback vua execute tung la blindspot |
| `new_hook_bonus` | `10` | Hook name chua tung xuat hien trong aggregate state |

## Cong thuc tong quat

```text
energy = sum(tier_weight(callback))
energy += blindspot bonuses
energy += new hook bonuses
score = clamp(energy, min=1, max=max_energy)
```

## Cau hinh qua env vars

| Variable | Default | Mo ta |
|---|---|---|
| `FUZZER_ENERGY_CALLBACK_FIRST` | `12` | Weight cho callback first_seen |
| `FUZZER_ENERGY_CALLBACK_RARE` | `5` | Weight cho callback rare |
| `FUZZER_ENERGY_CALLBACK_FREQUENT` | `1` | Weight cho callback frequent |
| `FUZZER_ENERGY_RARE_CALLBACK_MAX` | `3` | Nguong toi da van con la rare |
| `FUZZER_ENERGY_BLINDSPOT_BONUS` | `8` | Bonus khi callback blindspot duoc kich hoat |
| `FUZZER_ENERGY_NEW_HOOK_BONUS` | `10` | Bonus khi gap hook name moi |
| `FUZZER_ENERGY_MAX` | `200` | Tran tren cua score |

## Cau truc code hien tai

```text
fuzzer-core/fuzzing/
|-- energy.py                  # wrapper tuong thich
|-- watch_energy.py            # utility watcher
`-- energy/
    |-- __init__.py
    |-- calculator.py
    |-- cli_watch.py
    |-- config.py
    |-- models.py
    |-- request_store.py
    |-- scheduler.py
    `-- state.py
```

## Trang thai hien tai

- Energy da tach khoi PHP shutdown scoring
- Python side la noi aggregate state song
- Python watcher khong con ghi de `output/total_coverage.json`
- PHP runtime la source of truth cho aggregate coverage trong `output/total_coverage.json`
- `watch_energy.py` co the dung de demo hoac debug
- Chua co production mutation loop day du trong repo nay

## Huong di tiep theo

1. Noi `EnergyScheduler` vao loop fuzzer that
2. Phat hanh feedback fields on dinh nhu `new_callback_ids`, `rare_callback_ids`, `score`
3. Tach ro callback `stable_id` va `runtime_id` de giam collision

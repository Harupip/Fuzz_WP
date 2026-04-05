<?php
/**
 * Fuzz-only scoring helpers for UOPZ hook coverage.
 *
 * Muc tieu:
 * - Tach logic energy ra khoi file instrumentation
 * - Giu toan bo policy "first_seen / rare / frequent" o mot noi
 * - Cho phep scheduler/fuzzer ve sau dung lai ma khong phu thuoc chi tiet hook internals
 */

function __uopz_fuzz_env_int(string $name, int $default): int
{
    $value = getenv($name);
    if ($value === false || $value === '') {
        return $default;
    }

    return is_numeric($value) ? (int) $value : $default;
}

function __uopz_fuzz_default_energy(): array
{
    return [
        'score' => 1,
        'dominant_tier' => 'no_coverage',
        'weights' => [],
        'thresholds' => [],
        'components' => [],
        'totals' => [
            'unique_executed_callbacks' => 0,
        ],
    ];
}

function __uopz_fuzz_energy_weights(): array
{
    return [
        'callbacks' => [
            'first_seen' => __uopz_fuzz_env_int('FUZZER_ENERGY_CALLBACK_FIRST', 12),
            'rare' => __uopz_fuzz_env_int('FUZZER_ENERGY_CALLBACK_RARE', 5),
            'frequent' => __uopz_fuzz_env_int('FUZZER_ENERGY_CALLBACK_FREQUENT', 1),
        ],
    ];
}

function __uopz_fuzz_energy_thresholds(): array
{
    return [
        'rare_callback_max_count' => max(1, __uopz_fuzz_env_int('FUZZER_ENERGY_RARE_CALLBACK_MAX', 3)),
    ];
}

function __uopz_fuzz_energy_tier(int $historicalCount, int $rareMax): string
{
    if ($historicalCount <= 0) {
        return 'first_seen';
    }

    if ($historicalCount <= $rareMax) {
        return 'rare';
    }

    return 'frequent';
}

function __uopz_fuzz_empty_energy_bucket(): array
{
    return [
        'count' => 0,
        'energy' => 0,
        'items' => [],
    ];
}

function __uopz_fuzz_energy_template(): array
{
    return [
        'first_seen' => __uopz_fuzz_empty_energy_bucket(),
        'rare' => __uopz_fuzz_empty_energy_bucket(),
        'frequent' => __uopz_fuzz_empty_energy_bucket(),
    ];
}

function __uopz_fuzz_calculate_request_energy(
    array $requestHookCoverage,
    array $existingExecutedCallbacks
): array {
    $weights = __uopz_fuzz_energy_weights();
    $thresholds = __uopz_fuzz_energy_thresholds();
    $executedCallbacks = $requestHookCoverage['executed_callbacks'] ?? [];

    $components = [
        'callbacks' => __uopz_fuzz_energy_template(),
    ];

    $summaryCounts = [
        'first_seen' => 0,
        'rare' => 0,
        'frequent' => 0,
    ];

    $totalEnergy = 0;

    foreach ($executedCallbacks as $callbackId => $item) {
        $historicalCount = (int) ($existingExecutedCallbacks[$callbackId]['executed_count'] ?? 0);
        $tier = __uopz_fuzz_energy_tier($historicalCount, $thresholds['rare_callback_max_count']);
        $energy = (int) ($weights['callbacks'][$tier] ?? 1);

        $components['callbacks'][$tier]['count']++;
        $components['callbacks'][$tier]['energy'] += $energy;
        $components['callbacks'][$tier]['items'][] = [
            'callback_id' => $callbackId,
            'hook_name' => (string) ($item['hook_name'] ?? 'unknown'),
            'callback_repr' => (string) ($item['callback_repr'] ?? 'unknown_callback'),
            'previous_executed_count' => $historicalCount,
            'request_executed_count' => (int) ($item['executed_count'] ?? 1),
            'energy' => $energy,
        ];

        $summaryCounts[$tier]++;
        $totalEnergy += $energy;
    }

    $dominantTier = 'no_coverage';
    foreach (['first_seen', 'rare', 'frequent'] as $tier) {
        if ($summaryCounts[$tier] > 0) {
            $dominantTier = $tier;
            break;
        }
    }

    return [
        'score' => max(1, $totalEnergy),
        'dominant_tier' => $dominantTier,
        'weights' => $weights,
        'thresholds' => $thresholds,
        'components' => $components,
        'totals' => [
            'unique_executed_callbacks' => count($executedCallbacks),
        ],
        'summary' => [
            'first_seen_items' => $summaryCounts['first_seen'],
            'rare_items' => $summaryCounts['rare'],
            'frequent_items' => $summaryCounts['frequent'],
        ],
    ];
}


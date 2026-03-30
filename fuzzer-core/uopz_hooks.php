<?php
/**
 * UOPZ Hook Instrumentation for Fuzzing
 * 
 * Auto-prepend file: chạy TRƯỚC mọi file PHP.
 * Sử dụng UOPZ extension để hook vào các hàm core (add_action, apply_filters...)
 *
 * Output:
 *   - /var/www/uopz/output/requests/{request_id}.json
 *   - /var/www/uopz/output/total_coverage.json
 */

$__uopz_start_time = microtime(true);
$__uopz_hook_order = 0;

$__uopz_request = [
    'request_id'     => uniqid() . '-' . bin2hex(random_bytes(4)),
    'timestamp'      => date('Y-m-d H:i:s'),
    'http_method'    => $_SERVER['REQUEST_METHOD'] ?? 'CLI',
    'http_target'    => $_SERVER['REQUEST_URI'] ?? '',
    'request_params' => [
        'query_params' => $_GET ?? [],
        'body_params'  => $_POST ?? [],
        'headers'      => function_exists('getallheaders') ? getallheaders() : [],
        'cookies'      => isset($_COOKIE) ? array_keys($_COOKIE) : [],
    ],
    'hooks_timeline'  => [],
    'errors'          => [],
    'response'        => [
        'status_code' => 200,
        'time_ms'     => 0,
    ],
    'hook_coverage'   => [
        'registered' => [],
        'executed'   => [],
        'blindspots' => [],
    ],
];

// PHP Error Handler: Chụp lỗi vào Fuzzer Request Timeline
set_error_handler(function($errno, $errstr, $errfile, $errline) {
    global $__uopz_request;
    $__uopz_request['errors'][] = [
        'errno'   => $errno,
        'errstr'  => $errstr,
        'errfile' => $errfile,
        'errline' => $errline,
    ];
    // Trả về false để PHP vẫn in lỗi bình thường nếu cần (hoặc true để giấu lỗi đi)
    return false;
});

function __get_fuzzer_target() {
    // Dynamic fetching from Docker env var (.env file)
    $target = getenv('TARGET_APP_PATH');
    if (!$target) {
        $target = '/wp-content/plugins/'; // Default fallback
    }
    return $target;
}

function __is_target_app_code() {
    $target = __get_fuzzer_target();
    $backtrace = debug_backtrace(DEBUG_BACKTRACE_IGNORE_ARGS);
    
    foreach ($backtrace as $t) {
        if (isset($t['file'])) {
            $normalized_path = str_replace('\\', '/', $t['file']);
            if (strpos($normalized_path, $target) !== false) {
                // error_log("[FUZZER_DEBUG] Match found: $normalized_path matches $target");
                return true;
            }
        }
    }
    // Debug logging for non-matches (uncomment only if needed to avoid log spam)
    // error_log("[FUZZER_DEBUG] No match for target $target in backtrace: " . count($backtrace) . " frames");
    return false;
}

function __get_caller_info() {
    $target = __get_fuzzer_target();
    foreach (debug_backtrace(DEBUG_BACKTRACE_IGNORE_ARGS) as $t) {
        if (isset($t['file']) && strpos(str_replace('\\', '/', $t['file']), $target) !== false) {
            return basename($t['file']) . ':' . ($t['line'] ?? '?');
        }
    }
    return 'framework-core';
}

// ============================================================================
// HOOK ĐĂNG KÝ (Registered)
// ============================================================================

$res1 = uopz_set_hook('add_filter', function(...$args) {
    global $__uopz_request, $__uopz_hook_order;
    $hook = $args[0] ?? 'unknown';

    if (__is_target_app_code()) {
        $__uopz_hook_order++;
        $__uopz_request['hooks_timeline'][] = [
            'order'       => $__uopz_hook_order,
            'type'        => 'filter',
            'event'       => 'registered',
            'hook_name'   => $hook,
            'called_from' => __get_caller_info(),
        ];
        if (!in_array($hook, $__uopz_request['hook_coverage']['registered'])) {
            $__uopz_request['hook_coverage']['registered'][] = $hook;
        }
    }
});
if (!$res1) error_log("[FUZZER] Failed to hook add_filter");

$res2 = uopz_set_hook('add_action', function(...$args) {
    global $__uopz_request, $__uopz_hook_order;
    $hook = $args[0] ?? 'unknown';

    if (__is_target_app_code()) {
        $__uopz_hook_order++;
        $__uopz_request['hooks_timeline'][] = [
            'order'       => $__uopz_hook_order,
            'type'        => 'action',
            'event'       => 'registered',
            'hook_name'   => $hook,
            'called_from' => __get_caller_info(),
        ];
        if (!in_array($hook, $__uopz_request['hook_coverage']['registered'])) {
            $__uopz_request['hook_coverage']['registered'][] = $hook;
        }
    }
});
if (!$res2) error_log("[FUZZER] Failed to hook add_action");

// ============================================================================
// HOOK THỰC THI (Executed)
// ============================================================================

$res3 = uopz_set_hook('apply_filters', function(...$args) {
    global $__uopz_request, $__uopz_hook_order;
    $hook = $args[0] ?? 'unknown';

    $is_registered = in_array($hook, $__uopz_request['hook_coverage']['registered']);
    $is_from_app = __is_target_app_code();

    if ($is_registered || $is_from_app) {
        $__uopz_hook_order++;
        $__uopz_request['hooks_timeline'][] = [
            'order'       => $__uopz_hook_order,
            'type'        => 'filter',
            'event'       => 'executed',
            'hook_name'   => $hook,
            'called_from' => __get_caller_info(),
        ];
        if (!in_array($hook, $__uopz_request['hook_coverage']['executed'])) {
            $__uopz_request['hook_coverage']['executed'][] = $hook;
        }
    }
});
if (!$res3) error_log("[FUZZER] Failed to hook apply_filters");

$res4 = uopz_set_hook('do_action', function(...$args) {
    global $__uopz_request, $__uopz_hook_order;
    $hook = $args[0] ?? 'unknown';

    $is_registered = in_array($hook, $__uopz_request['hook_coverage']['registered']);
    $is_from_app = __is_target_app_code();

    if ($is_registered || $is_from_app) {
        $__uopz_hook_order++;
        $__uopz_request['hooks_timeline'][] = [
            'order'       => $__uopz_hook_order,
            'type'        => 'action',
            'event'       => 'executed',
            'hook_name'   => $hook,
            'called_from' => __get_caller_info(),
        ];
        if (!in_array($hook, $__uopz_request['hook_coverage']['executed'])) {
            $__uopz_request['hook_coverage']['executed'][] = $hook;
        }
    }
});
if (!$res4) error_log("[FUZZER] Failed to hook do_action");

// ============================================================================
// EXPORT KẾT QUẢ KHI REQUEST KẾT THÚC
// ============================================================================

register_shutdown_function(function() {
    global $__uopz_request, $__uopz_start_time;

    $__uopz_request['response']['status_code'] = http_response_code();
    $__uopz_request['response']['time_ms'] = round((microtime(true) - $__uopz_start_time) * 1000, 2);

    // Tính blindspots : Các hook có đăng ký nhưng không bao giờ được Framework gọi tới (Chính là mục tiêu tấn công tốt nhất)
    $__uopz_request['hook_coverage']['blindspots'] = array_values(
        array_diff(
            $__uopz_request['hook_coverage']['registered'],
            $__uopz_request['hook_coverage']['executed']
        )
    );

    // Thư mục output được gắn (Mount) từ máy Windows vào Docker
    $baseDir     = '/var/www/uopz/output';
    $requestsDir = $baseDir . '/requests';
    if (!is_dir($requestsDir)) @mkdir($requestsDir, 0777, true);

    // 1. Export JSON cho luồng hiện tại
    file_put_contents(
        $requestsDir . '/' . $__uopz_request['request_id'] . '.json',
        json_encode($__uopz_request, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)
    );

    // 2. Export File báo cáo tổng hợp quá trình Fuzzing
    $coverageFile = $baseDir . '/total_coverage.json';
    $existing = [];
    if (file_exists($coverageFile)) {
        $existing = json_decode(file_get_contents($coverageFile), true) ?? [];
    }

    $allReg  = array_values(array_unique(array_merge(
        $existing['data']['registered_by_app'] ?? [],
        $__uopz_request['hook_coverage']['registered']
    )));
    $allExec = array_values(array_unique(array_merge(
        $existing['data']['actually_executed'] ?? [],
        $__uopz_request['hook_coverage']['executed']
    )));

    $covered   = array_values(array_intersect($allReg, $allExec));
    $uncovered = array_values(array_diff($allReg, $allExec));

    $total = [
        'metadata' => [
            'total_target_hooks'    => count($allReg),
            'coverage_percent'      => count($allReg) > 0
                ? round((count($covered) / count($allReg)) * 100, 2) . '%'
                : '0%',
            'total_requests_logged' => count(glob($requestsDir . '/*.json')),
            'last_request_time'     => date('Y-m-d H:i:s'),
            'last_request_id'       => $__uopz_request['request_id'],
        ],
        'data' => [
            'registered_by_app' => $allReg,
            'actually_executed' => $covered,
            'fuzzer_blindspots' => $uncovered,
        ],
    ];

    file_put_contents($coverageFile, json_encode($total, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
});

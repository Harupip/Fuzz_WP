<?php
/**
 * UOPZ Hook Instrumentation for WordPress
 * 
 * Auto-prepend file: chạy TRƯỚC mọi file PHP của WordPress.
 * Sử dụng UOPZ extension để hook vào add_action/add_filter/do_action/apply_filters
 * và ghi lại luồng thực thi chi tiết cho từng HTTP request.
 *
 * Output:
 *   - Per-request:  hook-coverage/requests/{request_id}.json
 *   - Tổng hợp:    hook-coverage/total_coverage.json
 */

// ============================================================================
// 1. KHỞI TẠO - Thu thập thông tin Request ngay khi PHP bắt đầu
// ============================================================================

$__uopz_start_time = microtime(true);
$__uopz_hook_order = 0;

$__uopz_request = [
    'request_id'     => uniqid() . '-' . bin2hex(random_bytes(4)),
    'timestamp'      => date('Y-m-d H:i:s'),
    'http_method'    => $_SERVER['REQUEST_METHOD'] ?? 'CLI',
    'http_target'    => $_SERVER['REQUEST_URI'] ?? '',
    'request_params' => [
        'query_params' => $_GET,
        'body_params'  => $_POST,
        'headers'      => function_exists('getallheaders') ? getallheaders() : [],
        'cookies'      => array_keys($_COOKIE),
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

// ============================================================================
// 2. ERROR HANDLER - Bắt lỗi PHP trong request
// ============================================================================

set_error_handler(function($errno, $errstr, $errfile, $errline) {
    global $__uopz_request;
    $__uopz_request['errors'][] = [
        'errno'   => $errno,
        'errstr'  => $errstr,
        'errfile' => $errfile,
        'errline' => $errline,
    ];
    return false;
});

// ============================================================================
// 3. HÀM PHỤ TRỢ
// ============================================================================

function __is_target_plugin_hook() {
    $target = '/wp-content/plugins/shop-demo/';
    foreach (debug_backtrace(DEBUG_BACKTRACE_IGNORE_ARGS) as $t) {
        if (isset($t['file']) && strpos(str_replace('\\', '/', $t['file']), $target) !== false) {
            return true;
        }
    }
    return false;
}

function __get_caller_info() {
    $target = '/wp-content/plugins/shop-demo/';
    foreach (debug_backtrace(DEBUG_BACKTRACE_IGNORE_ARGS) as $t) {
        if (isset($t['file']) && strpos(str_replace('\\', '/', $t['file']), $target) !== false) {
            return basename($t['file']) . ':' . ($t['line'] ?? '?');
        }
    }
    return 'wordpress-core';
}

// ============================================================================
// 4. HOOK ĐĂNG KÝ: add_filter / add_action
// ============================================================================

uopz_set_return('add_filter', function(...$args) {
    global $__uopz_request, $__uopz_hook_order;
    $hook = $args[0] ?? 'unknown';

    if (__is_target_plugin_hook()) {
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
    return \add_filter(...$args);
}, true);

uopz_set_return('add_action', function(...$args) {
    global $__uopz_request, $__uopz_hook_order;
    $hook = $args[0] ?? 'unknown';

    if (__is_target_plugin_hook()) {
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
    return \add_action(...$args);
}, true);

// ============================================================================
// 5. HOOK THỰC THI: apply_filters / do_action
// ============================================================================

uopz_set_return('apply_filters', function(...$args) {
    global $__uopz_request, $__uopz_hook_order;
    $hook = $args[0] ?? 'unknown';

    $is_registered = in_array($hook, $__uopz_request['hook_coverage']['registered']);
    $is_from_plugin = __is_target_plugin_hook();

    if ($is_registered || $is_from_plugin) {
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
    return \apply_filters(...$args);
}, true);

uopz_set_return('do_action', function(...$args) {
    global $__uopz_request, $__uopz_hook_order;
    $hook = $args[0] ?? 'unknown';

    $is_registered = in_array($hook, $__uopz_request['hook_coverage']['registered']);
    $is_from_plugin = __is_target_plugin_hook();

    if ($is_registered || $is_from_plugin) {
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
    return \do_action(...$args);
}, true);

// ============================================================================
// 6. SHUTDOWN - Ghi báo cáo khi request kết thúc
// ============================================================================

register_shutdown_function(function() {
    global $__uopz_request, $__uopz_start_time;

    // Tính response
    $__uopz_request['response']['status_code'] = http_response_code();
    $__uopz_request['response']['time_ms'] = round((microtime(true) - $__uopz_start_time) * 1000, 2);

    // Tính blindspots
    $__uopz_request['hook_coverage']['blindspots'] = array_values(
        array_diff(
            $__uopz_request['hook_coverage']['registered'],
            $__uopz_request['hook_coverage']['executed']
        )
    );

    $baseDir     = __DIR__ . '/hook-coverage';
    $requestsDir = $baseDir . '/requests';
    if (!is_dir($requestsDir)) @mkdir($requestsDir, 0777, true);

    // A. Per-request report
    file_put_contents(
        $requestsDir . '/' . $__uopz_request['request_id'] . '.json',
        json_encode($__uopz_request, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)
    );

    // B. Aggregate coverage report
    $coverageFile = $baseDir . '/total_coverage.json';
    $existing = [];
    if (file_exists($coverageFile)) {
        $existing = json_decode(file_get_contents($coverageFile), true) ?? [];
    }

    $allReg  = array_values(array_unique(array_merge(
        $existing['data']['registered_by_plugin'] ?? [],
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
            'registered_by_plugin' => $allReg,
            'actually_executed'    => $covered,
            'blindspots'           => $uncovered,
        ],
    ];

    file_put_contents($coverageFile, json_encode($total, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
});

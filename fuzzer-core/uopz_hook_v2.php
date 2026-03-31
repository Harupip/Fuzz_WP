<?php
/**
 * UOPZ Hook Instrumentation for WordPress Fuzzing - Refactor v2
 *
 * Mục tiêu:
 * - Theo dõi callback-level registration
 * - Theo dõi hook fired
 * - Theo dõi callback-level dispatch (best effort qua WP_Hook)
 * - Export per-request + aggregate coverage
 *
 * Gợi ý triển khai:
 * - Có thể include file này từ MU plugin sớm
 * - Hoặc auto_prepend_file + gọi lại __uopz_install_wp_hooks() khi WP đã load xong plugin.php
 */

// ============================================================================
// GLOBAL STATE
// ============================================================================

// Mốc thời gian bắt đầu request để tính tổng thời gian xử lý ở cuối request.
$GLOBALS['__uopz_start_time'] = microtime(true);
// Bộ đếm tăng dần để timeline giữ đúng thứ tự xảy ra của các sự kiện.
$GLOBALS['__uopz_hook_order'] = 0;
// Cờ chặn việc cài hook lặp lại nhiều lần trong cùng một request.
$GLOBALS['__uopz_hooks_installed'] = false;
$GLOBALS['__uopz_hook_failures'] = [];

// Tạo request_id thân thiện: <Giờ-Phút-Giây>_<Method>_<Path>_<Random>
$__uopz_method = $_SERVER['REQUEST_METHOD'] ?? 'CLI';
$__uopz_uri = $_SERVER['REQUEST_URI'] ?? '';
$__uopz_path = parse_url($__uopz_uri, PHP_URL_PATH) ?: '';
$__uopz_slug = trim(str_replace(['/', '.', '?', '&', '='], '_', $__uopz_path), '_') ?: 'index';
$__uopz_slug = substr($__uopz_slug, 0, 30);

// Đây là payload chính sẽ được ghi ra JSON khi request kết thúc.
$GLOBALS['__uopz_request'] = [
    'request_id' => date('His') . "_{$__uopz_method}_{$__uopz_slug}_" . bin2hex(random_bytes(2)),
    'timestamp' => date('Y-m-d H:i:s'),
    'http_method' => $__uopz_method,
    'http_target' => $__uopz_uri,
    'request_params' => [
        'query_params' => $_GET ?? [],
        'body_params' => $_POST ?? [],
        'headers' => function_exists('getallheaders') ? getallheaders() : [],
        'cookies' => isset($_COOKIE) ? array_keys($_COOKIE) : [],
    ],
    'hooks_timeline' => [],
    'errors' => [],
    'response' => [
        'status_code' => 200,
        'time_ms' => 0,
    ],
    'hook_coverage' => [
        // callback-level
        'registered_callbacks' => [],   // callback_id => data
        'executed_callbacks' => [],   // callback_id => data
        'blindspot_callbacks' => [],   // callback_id => data

        // hook-level
        'fired_hooks' => [],   // unique hook names that fired
    ],
    'debug' => [
        'target_app_path' => null,
        'install_failures' => [],
    ],
];

// ============================================================================
// CONFIG
// ============================================================================

function __get_fuzzer_target(): string
{
    // TARGET_APP_PATH dùng để lọc frame nào thực sự thuộc plugin/app mục tiêu.
    $target = getenv('TARGET_APP_PATH');
    if (!$target) {
        $target = '/wp-content/plugins/';
    }
    $target = str_replace('\\', '/', $target);
    $GLOBALS['__uopz_request']['debug']['target_app_path'] = $target;
    return $target;
}

function __uopz_base_dir(): string
{
    return '/var/www/uopz/output';
}

function __uopz_requests_dir(): string
{
    return __uopz_base_dir() . '/requests';
}

function __uopz_should_persist_request(): bool
{
    $method = strtoupper((string) ($GLOBALS['__uopz_request']['http_method'] ?? 'CLI'));
    $target = (string) ($GLOBALS['__uopz_request']['http_target'] ?? '');
    $path = parse_url($target, PHP_URL_PATH) ?: '';
    $path = strtolower(rtrim($path, '/'));

    if ($method === 'CLI') {
        return false;
    }

    if ($path === '') {
        return true;
    }

    if ($path === '/favicon.ico') {
        return false;
    }

    if (strpos($path, '/.well-known/') === 0) {
        return false;
    }

    // Skip static/assets requests because they add little value for hook coverage.
    if (preg_match('/\.(css|js|map|png|jpe?g|gif|svg|ico|webp|avif|bmp|woff2?|ttf|eot|otf|mp4|webm|mp3|wav|pdf|txt|xml)$/', $path)) {
        return false;
    }

    return true;
}

// ============================================================================
// LOW-LEVEL HELPERS
// ============================================================================

set_error_handler(function ($errno, $errstr, $errfile, $errline) {
    $GLOBALS['__uopz_request']['errors'][] = [
        'errno' => $errno,
        'errstr' => $errstr,
        'errfile' => $errfile,
        'errline' => $errline,
    ];

    return false;
});

function __uopz_next_order(): int
{
    $GLOBALS['__uopz_hook_order']++;
    return $GLOBALS['__uopz_hook_order'];
}

function __uopz_limit_backtrace(int $limit = 12): array
{
    // Giới hạn backtrace để giảm overhead vì helper này bị gọi rất thường xuyên.
    return debug_backtrace(DEBUG_BACKTRACE_IGNORE_ARGS, $limit);
}

function __uopz_path_matches_target(?string $file): bool
{
    if (!$file) {
        return false;
    }

    $target = __get_fuzzer_target();
    $normalized = str_replace('\\', '/', $file);

    return strpos($normalized, $target) !== false;
}

function __is_target_app_code(): bool
{
    // Chỉ cần có một frame match target app là xem như hành động này đến từ app cần fuzz.
    foreach (__uopz_limit_backtrace(10) as $frame) {
        if (isset($frame['file']) && __uopz_path_matches_target($frame['file'])) {
            return true;
        }
    }
    return false;
}

function __get_caller_info(): string
{
    // Lấy file:line gần nhất thuộc target app để log gọn và dễ đọc.
    foreach (__uopz_limit_backtrace(12) as $frame) {
        if (isset($frame['file']) && __uopz_path_matches_target($frame['file'])) {
            return basename($frame['file']) . ':' . ($frame['line'] ?? '?');
        }
    }

    return 'framework-core';
}

function __uopz_safe_json($data): string
{
    return json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
}

function __uopz_callback_repr($callback): string
{
    // Chuẩn hóa callback của WordPress thành chuỗi ổn định để log và tạo ID.
    if (is_string($callback)) {
        return $callback;
    }

    if ($callback instanceof Closure) {
        return 'Closure';
    }

    if (is_array($callback) && count($callback) === 2) {
        [$target, $method] = $callback;

        if (is_object($target)) {
            return get_class($target) . '->' . $method;
        }

        if (is_string($target)) {
            return $target . '::' . $method;
        }
    }

    if (is_object($callback) && method_exists($callback, '__invoke')) {
        return get_class($callback) . '::__invoke';
    }

    return 'unknown_callback';
}

// callback_id la khoa de gom du lieu coverage o muc callback.
function __uopz_callback_id($callback, $hookName = '', $priority = null): string
{
    $repr = __uopz_callback_repr($callback);

    // callback-level identity, gắn thêm hook + priority để phân biệt cùng callback đăng ký ở nhiều nơi
    return sha1($hookName . '|' . (string) $priority . '|' . $repr);
}

// Ghi nhan callback duoc add_action/add_filter dang ky vao request hien tai.
function __uopz_register_callback(
    string $type,
    string $hookName,
    $callback,
    int $priority = 10,
    int $acceptedArgs = 1,
    string $source = 'register'
): void {
    $callbackId = __uopz_callback_id($callback, $hookName, $priority);
    $repr = __uopz_callback_repr($callback);

    if (!isset($GLOBALS['__uopz_request']['hook_coverage']['registered_callbacks'][$callbackId])) {
        $GLOBALS['__uopz_request']['hook_coverage']['registered_callbacks'][$callbackId] = [
            'callback_id' => $callbackId,
            'type' => $type,
            'hook_name' => $hookName,
            'callback_repr' => $repr,
            'priority' => $priority,
            'accepted_args' => $acceptedArgs,
            'registered_from' => __get_caller_info(),
            'source' => $source,
        ];
    }

    $GLOBALS['__uopz_request']['hooks_timeline'][] = [
        'order' => __uopz_next_order(),
        'type' => $type,
        'event' => 'registered',
        'hook_name' => $hookName,
        'callback_id' => $callbackId,
        'callback_repr' => $repr,
        'priority' => $priority,
        'accepted_args' => $acceptedArgs,
        'called_from' => __get_caller_info(),
        'source' => $source,
    ];
}

// Ghi nhan mot hook name da duoc fire, doc lap voi danh sach callback ben trong hook.
function __uopz_mark_hook_fired(string $type, string $hookName, string $source = 'runtime'): void
{
    if (!in_array($hookName, $GLOBALS['__uopz_request']['hook_coverage']['fired_hooks'], true)) {
        $GLOBALS['__uopz_request']['hook_coverage']['fired_hooks'][] = $hookName;
    }

    $GLOBALS['__uopz_request']['hooks_timeline'][] = [
        'order' => __uopz_next_order(),
        'type' => $type,
        'event' => 'hook_fired',
        'hook_name' => $hookName,
        'called_from' => __get_caller_info(),
        'source' => $source,
    ];
}

// Ghi nhan callback nam trong danh sach ma WP_Hook se dispatch cho hook hien tai.
function __uopz_mark_callback_executed(
    string $type,
    string $hookName,
    $callback,
    int $priority = 10,
    int $acceptedArgs = 1,
    string $source = 'dispatch'
): void {
    $callbackId = __uopz_callback_id($callback, $hookName, $priority);
    $repr = __uopz_callback_repr($callback);

    if (!isset($GLOBALS['__uopz_request']['hook_coverage']['executed_callbacks'][$callbackId])) {
        $GLOBALS['__uopz_request']['hook_coverage']['executed_callbacks'][$callbackId] = [
            'callback_id' => $callbackId,
            'type' => $type,
            'hook_name' => $hookName,
            'callback_repr' => $repr,
            'priority' => $priority,
            'accepted_args' => $acceptedArgs,
            'executed_from' => __get_caller_info(),
            'source' => $source,
        ];
    }

    $GLOBALS['__uopz_request']['hooks_timeline'][] = [
        'order' => __uopz_next_order(),
        'type' => $type,
        'event' => 'callback_dispatched',
        'hook_name' => $hookName,
        'callback_id' => $callbackId,
        'callback_repr' => $repr,
        'priority' => $priority,
        'accepted_args' => $acceptedArgs,
        'called_from' => __get_caller_info(),
        'source' => $source,
    ];
}

// Duyet cau truc noi bo cua WP_Hook de lay snapshot callbacks theo priority.
function __uopz_dispatch_callbacks_from_wp_hook($wpHookObject, string $hookName, string $type): void
{
    if (!is_object($wpHookObject) || !isset($wpHookObject->callbacks) || !is_array($wpHookObject->callbacks)) {
        return;
    }

    foreach ($wpHookObject->callbacks as $priority => $callbacksAtPriority) {
        if (!is_array($callbacksAtPriority)) {
            continue;
        }

        foreach ($callbacksAtPriority as $entry) {
            if (!is_array($entry)) {
                continue;
            }

            $callback = $entry['function'] ?? null;
            $acceptedArgs = (int) ($entry['accepted_args'] ?? 1);

            if ($callback === null) {
                continue;
            }

            __uopz_mark_callback_executed(
                $type,
                $hookName,
                $callback,
                (int) $priority,
                $acceptedArgs,
                'wp_hook_snapshot'
            );
        }
    }
}

// Luu ly do cai hook that bai de debug luc auto_prepend chay qua som.
function __uopz_record_install_failure(string $name): void
{
    $GLOBALS['__uopz_hook_failures'][] = $name;
    $GLOBALS['__uopz_request']['debug']['install_failures'][] = $name;
}

// ============================================================================
// UOPZ INSTALLERS
// ============================================================================

// Thu gan hook vao ham global cua WP; neu ham chua ton tai thi chi log failure, khong fail cung.
function __uopz_try_hook_function(string $functionName, Closure $closure): bool
{
    if (!function_exists($functionName)) {
        __uopz_record_install_failure("function_missing:$functionName");
        return false;
    }

    $ok = @uopz_set_hook($functionName, $closure);
    if (!$ok) {
        __uopz_record_install_failure("hook_failed:$functionName");
    }

    return (bool) $ok;
}

// Thu gan hook vao method nhu WP_Hook::apply_filters / WP_Hook::do_action.
function __uopz_try_hook_method(string $className, string $methodName, Closure $closure): bool
{
    if (!class_exists($className, false) || !method_exists($className, $methodName)) {
        __uopz_record_install_failure("method_missing:$className::$methodName");
        return false;
    }

    $ok = @uopz_set_hook($className, $methodName, $closure);
    if (!$ok) {
        __uopz_record_install_failure("hook_failed:$className::$methodName");
    }

    return (bool) $ok;
}

// Day la diem cai dat chinh. Co the goi lai an toan sau khi WP load xong.
function __uopz_install_wp_hooks(): void
{
    if ($GLOBALS['__uopz_hooks_installed'] === true) {
        return;
    }

    if (!extension_loaded('uopz')) {
        __uopz_record_install_failure('extension_missing:uopz');
        return;
    }

    // ------------------------------------------------------------------------
    // Registration monitoring
    // ------------------------------------------------------------------------

    $installResults = [];

    $installResults[] = __uopz_try_hook_function('add_filter', function (...$args) {
        // Signature cua WP: add_filter($hook, $callback, $priority = 10, $accepted_args = 1)
        $hookName = (string) ($args[0] ?? 'unknown');
        $callback = $args[1] ?? null;
        $priority = (int) ($args[2] ?? 10);
        $acceptedArgs = (int) ($args[3] ?? 1);

        if ($callback === null) {
            return;
        }

        if (__is_target_app_code()) {
            __uopz_register_callback(
                'filter',
                $hookName,
                $callback,
                $priority,
                $acceptedArgs,
                'add_filter'
            );
        }
    });

    $installResults[] = __uopz_try_hook_function('add_action', function (...$args) {
        // add_action co shape du lieu giong add_filter, khac nhau o y nghia event.
        $hookName = (string) ($args[0] ?? 'unknown');
        $callback = $args[1] ?? null;
        $priority = (int) ($args[2] ?? 10);
        $acceptedArgs = (int) ($args[3] ?? 1);

        if ($callback === null) {
            return;
        }

        if (__is_target_app_code()) {
            __uopz_register_callback(
                'action',
                $hookName,
                $callback,
                $priority,
                $acceptedArgs,
                'add_action'
            );
        }
    });

    // ------------------------------------------------------------------------
    // Hook fire monitoring
    // ------------------------------------------------------------------------

    $installResults[] = __uopz_try_hook_function('apply_filters', function (...$args) {
        $hookName = (string) ($args[0] ?? 'unknown');

        // Log hook fired neu request dang cham vao target app
        // hoac app da dang ky callback truoc do trong request nay.
        if (__is_target_app_code() || !empty($GLOBALS['__uopz_request']['hook_coverage']['registered_callbacks'])) {
            __uopz_mark_hook_fired('filter', $hookName, 'apply_filters');
        }
    });

    $installResults[] = __uopz_try_hook_function('do_action', function (...$args) {
        $hookName = (string) ($args[0] ?? 'unknown');

        if (__is_target_app_code() || !empty($GLOBALS['__uopz_request']['hook_coverage']['registered_callbacks'])) {
            __uopz_mark_hook_fired('action', $hookName, 'do_action');
        }
    });

    // ------------------------------------------------------------------------
    // Callback dispatch monitoring (best effort qua WP_Hook)
    // ------------------------------------------------------------------------
    // Lưu ý:
    // - uopz_set_hook trên method chạy ở đầu method
    // - ta snapshot danh sách callbacks mà WP_Hook sẽ iterate
    // - điều này gần callback-level execution hơn rất nhiều so với chỉ log do_action/apply_filters

    // Hook vao WP_Hook::apply_filters de nhin thay danh sach callback o muc thap hon ten hook.
    $installResults[] = __uopz_try_hook_method('WP_Hook', 'apply_filters', function (...$args) {
        // Method signature thực tế của WP_Hook::apply_filters khác nhau theo version,
        // nên ta không phụ thuộc chặt vào arg positions.
        // Hook name thường lấy được từ current_filter().
        $hookName = function_exists('current_filter') ? (string) current_filter() : 'unknown_filter';

        if (!isset($GLOBALS['wp_filter'][$hookName]) || !is_object($GLOBALS['wp_filter'][$hookName])) {
            return;
        }

        __uopz_dispatch_callbacks_from_wp_hook($GLOBALS['wp_filter'][$hookName], $hookName, 'filter');
    });

    // Hook vao WP_Hook::do_action voi muc dich tuong tu cho action hooks.
    $installResults[] = __uopz_try_hook_method('WP_Hook', 'do_action', function (...$args) {
        $hookName = function_exists('current_filter') ? (string) current_filter() : 'unknown_action';

        if (!isset($GLOBALS['wp_filter'][$hookName]) || !is_object($GLOBALS['wp_filter'][$hookName])) {
            return;
        }

        __uopz_dispatch_callbacks_from_wp_hook($GLOBALS['wp_filter'][$hookName], $hookName, 'action');
    });

    // auto_prepend co the chay truoc khi WordPress load xong plugin API.
    // Neu danh dau "installed" qua som thi MU plugin se khong retry duoc nua.
    $GLOBALS['__uopz_hooks_installed'] = !in_array(false, $installResults, true);
}

// ============================================================================
// AGGREGATION
// ============================================================================

// Blindspot cua v2 = callback da register nhung chua xuat hien trong executed_callbacks.
function __uopz_compute_blindspots(): void
{
    $registered = $GLOBALS['__uopz_request']['hook_coverage']['registered_callbacks'];
    $executed = $GLOBALS['__uopz_request']['hook_coverage']['executed_callbacks'];

    $blindspots = [];

    foreach ($registered as $callbackId => $data) {
        if (!isset($executed[$callbackId])) {
            $blindspots[$callbackId] = $data;
        }
    }

    $GLOBALS['__uopz_request']['hook_coverage']['blindspot_callbacks'] = $blindspots;
}

// Ghi file qua temp + rename de tranh JSON dang do khi request bi ngat giua chung.
function __uopz_write_json_atomic(string $path, array $data): void
{
    $tmp = $path . '.tmp.' . bin2hex(random_bytes(4));
    file_put_contents($tmp, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
    rename($tmp, $path);
}

// Merge du lieu request hien tai vao file tong hop dung chung cho nhieu request fuzz.
function __uopz_update_total_coverage(): void
{
    $baseDir = __uopz_base_dir();
    $requestsDir = __uopz_requests_dir();
    $coverageFile = $baseDir . '/total_coverage.json';
    $lockFile = $baseDir . '/total_coverage.lock';

    if (!is_dir($requestsDir)) {
        @mkdir($requestsDir, 0777, true);
    }

    // Lock file de tranh hai request ghi total_coverage.json cung luc.
    $lockFp = fopen($lockFile, 'c+');
    if (!$lockFp) {
        return;
    }

    if (!flock($lockFp, LOCK_EX)) {
        fclose($lockFp);
        return;
    }

    try {
        $existing = [];
        if (file_exists($coverageFile)) {
            $existing = json_decode(file_get_contents($coverageFile), true) ?? [];
        }

        $existingRegistered = $existing['data']['registered_callbacks'] ?? [];
        $existingExecuted = $existing['data']['executed_callbacks'] ?? [];

        $currentRegistered = $GLOBALS['__uopz_request']['hook_coverage']['registered_callbacks'];
        $currentExecuted = $GLOBALS['__uopz_request']['hook_coverage']['executed_callbacks'];

        // Merge theo callback_id de du lieu aggregate khong bi duplicate.
        $allRegistered = $existingRegistered;
        foreach ($currentRegistered as $id => $item) {
            $allRegistered[$id] = $item;
        }

        $allExecuted = $existingExecuted;
        foreach ($currentExecuted as $id => $item) {
            $allExecuted[$id] = $item;
        }

        // executed_callbacks o muc aggregate chi nen tinh tren callback cua target app
        // da tung register, neu khong tu so se bi doi len boi callback core WordPress.
        $coveredExecuted = [];
        $blindspots = [];
        foreach ($allRegistered as $id => $item) {
            if (isset($allExecuted[$id])) {
                $coveredExecuted[$id] = $allExecuted[$id];
                continue;
            }

            $blindspots[$id] = $item;
        }

        $coveredCount = count($allRegistered) > 0
            ? round((count($coveredExecuted) / count($allRegistered)) * 100, 2)
            : 0.0;

        $total = [
            'metadata' => [
                'total_registered_callbacks' => count($allRegistered),
                'total_executed_callbacks' => count($coveredExecuted),
                'coverage_percent' => $coveredCount . '%',
                'last_request_time' => date('Y-m-d H:i:s'),
                'last_request_id' => $GLOBALS['__uopz_request']['request_id'],
                'install_failures' => $GLOBALS['__uopz_request']['debug']['install_failures'],
            ],
            'data' => [
                'registered_callbacks' => $allRegistered,
                'executed_callbacks' => $coveredExecuted,
                'blindspot_callbacks' => $blindspots,
            ],
        ];

        __uopz_write_json_atomic($coverageFile, $total);
    } finally {
        flock($lockFp, LOCK_UN);
        fclose($lockFp);
    }
}

// ============================================================================
// SHUTDOWN EXPORT
// ============================================================================

register_shutdown_function(function () {
    // Flush o shutdown de thu du errors, status code va timeline cuoi cung cua request.
    $GLOBALS['__uopz_request']['response']['status_code'] =
        function_exists('http_response_code') ? http_response_code() : 200;

    $GLOBALS['__uopz_request']['response']['time_ms'] =
        round((microtime(true) - $GLOBALS['__uopz_start_time']) * 1000, 2);

    __uopz_compute_blindspots();

    $requestsDir = __uopz_requests_dir();
    if (!is_dir($requestsDir)) {
        @mkdir($requestsDir, 0777, true);
    }

    if (!__uopz_should_persist_request()) {
        return;
    }

    $requestFile = $requestsDir . '/' . $GLOBALS['__uopz_request']['request_id'] . '.json';
    __uopz_write_json_atomic($requestFile, $GLOBALS['__uopz_request']);

    __uopz_update_total_coverage();
});

// ============================================================================
// BOOTSTRAP
// ============================================================================

// Thử install ngay.
// Nếu lúc này WordPress core chưa load add_action/do_action/WP_Hook,
// bạn có thể gọi lại __uopz_install_wp_hooks() sau khi plugin.php đã được load.
// Co the goi lai ham nay sau khi WordPress load xong neu auto_prepend chay qua som.
__uopz_install_wp_hooks();

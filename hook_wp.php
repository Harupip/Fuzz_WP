<?php

// 1. Biến toàn cục để lưu trữ trạng thái các Hook trong suốt vòng đời của 1 Request
global $__fuzzer_hook_coverage;
$__fuzzer_hook_coverage = [
    'registered' => [],
    'executed'   => []
];

// Hàm phụ trợ để kiểm tra xem Hook này có phải do Plugin mục tiêu đăng ký không 
// (Tránh thu thập hàng ngàn Hook rác của WordPress Core)
function __is_target_plugin_hook() {
    // Đổi tên thư mục plugin của bạn ở đây
    $target_plugin_path = '/wp-content/plugins/your-target-plugin/';
    $traces = debug_backtrace(DEBUG_BACKTRACE_IGNORE_ARGS);
    foreach ($traces as $trace) {
        if (isset($trace['file'])) {
            $normalized_path = str_replace('\\', '/', $trace['file']);
            if (strpos($normalized_path, $target_plugin_path) !== false) {
                return true; 
            }
        }
    }
    return false;
}

// ==============================================================================
// 2. GIÁM SÁT CÁC HOOK ĐƯỢC ĐĂNG KÝ (add_filter / add_action)
// ==============================================================================

uopz_set_return('add_filter', function(...$args) {
    global $__fuzzer_hook_coverage;
    $hook_name = $args[0] ?? 'unknown_hook';
    
    // Nếu hàm này được gọi từ Plugin ta đang Fuzz, thì đánh dấu là "đã đăng ký"
    if (__is_target_plugin_hook()) {
        $__fuzzer_hook_coverage['registered'][$hook_name] = true;
    }

    // Đặc biệt của UOPZ: Trong Closure này, việc gọi lại hàm gốc (add_filter) 
    // KHÔNG gây lặp vô hạn. UOPZ tạm thời khôi phục hàm gốc để ta sử dụng.
    return \add_filter(...$args);
}, true);

uopz_set_return('add_action', function(...$args) {
    global $__fuzzer_hook_coverage;
    $hook_name = $args[0] ?? 'unknown_hook';
    
    if (__is_target_plugin_hook()) {
        $__fuzzer_hook_coverage['registered'][$hook_name] = true;
    }

    return \add_action(...$args);
}, true);

// ==============================================================================
// 3. GIÁM SÁT CÁC HOOK ĐƯỢC THỰC THI (apply_filters / do_action)
// ==============================================================================

uopz_set_return('apply_filters', function(...$args) {
    global $__fuzzer_hook_coverage;
    $hook_name = $args[0] ?? 'unknown_hook';
    $__fuzzer_hook_coverage['executed'][$hook_name] = true;

    return \apply_filters(...$args);
}, true);

uopz_set_return('do_action', function(...$args) {
    global $__fuzzer_hook_coverage;
    $hook_name = $args[0] ?? 'unknown_hook';
    $__fuzzer_hook_coverage['executed'][$hook_name] = true;

    return \do_action(...$args);
}, true);

// ==============================================================================
// 4. KẾT XUẤT BÁO CÁO CỦA REQUEST KHI KẾT THÚC (SHUTDOWN)
// ==============================================================================

// Hàm này sẽ chạy cuối cùng trước khi PHP đóng kết nối trả về cho người dùng
register_shutdown_function(function() {
    global $__fuzzer_hook_coverage;
    
    $registered = array_keys($__fuzzer_hook_coverage['registered']);
    $executed   = array_keys($__fuzzer_hook_coverage['executed']);
    
    // Giao của 2 tập hợp (chỉ cho request hiện tại - cho mục đích log chi tiết nếu cần, nhưng ta sẽ gộp chung)
    
    // Ghi báo cáo ra MỘT file duy nhất
    $reportPath = __DIR__ . '/hook-coverage/total_coverage.json';
    
    $existing = [];
    if (file_exists($reportPath)) {
        $json_str = file_get_contents($reportPath);
        if (!empty($json_str)) {
            $existing = json_decode($json_str, true);
        }
    }
    
    // Lấy tập hợp cũ
    $all_registered = isset($existing['data']['registered_by_plugin']) ? $existing['data']['registered_by_plugin'] : [];
    $all_executed = isset($existing['data']['actually_executed']) ? $existing['data']['actually_executed'] : [];
    
    // Gộp và lọc trùng lặp
    $all_registered = array_values(array_unique(array_merge($all_registered, $registered)));
    $all_executed = array_values(array_unique(array_merge($all_executed, $executed)));
    
    // Tính toán lại giao và hiệu
    $covered_hooks = array_values(array_intersect($all_registered, $all_executed));
    $uncovered_hooks = array_values(array_diff($all_registered, $all_executed));
    
    $report = [
        'metadata' => [
            'total_target_hooks' => count($all_registered),
            'coverage_percent'   => count($all_registered) > 0 ? round((count($covered_hooks) / count($all_registered)) * 100, 2) . '%' : '0%',
            'last_request_time'  => date('Y-m-d H:i:s')
        ],
        'data' => [
            'registered_by_plugin' => $all_registered,
            'actually_executed'    => $covered_hooks,
            'fuzzer_blindspots'    => $uncovered_hooks // Những hook CHƯA TỪNG chạy từ trước đến nay
        ]
    ];
    
    // Đảm bảo thư mục tồn tại nếu chưa có
    if (!is_dir(dirname($reportPath))) {
        @mkdir(dirname($reportPath), 0777, true);
    }
    
    file_put_contents($reportPath, json_encode($report, JSON_PRETTY_PRINT));
});

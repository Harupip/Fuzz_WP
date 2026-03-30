<?php
/**
 * FUZZER ENGINE - Điểm khởi đầu của mọi ứng dụng.
 * Được nạp TỰ ĐỘNG BỞI PHP (thông qua auto_prepend_file trong php.ini).
 * Không được xóa hoặc đổi tên.
 */

// Lấy tham số cấu hình từ môi trường Docker
$enable_uopz = getenv('FUZZER_ENABLE_UOPZ') === '1';
$enable_pcov = getenv('FUZZER_ENABLE_PCOV') === '1';

// 1. Kích hoạt UOPZ Hooking (Giai đoạn đầu)
if ($enable_uopz) {
    if (file_exists(__DIR__ . '/uopz_hooks.php')) {
        require_once __DIR__ . '/uopz_hooks.php';
    }
}

// 2. Kích hoạt PCOV Coverage (Chuẩn bị cho Giai đoạn sau)
if ($enable_pcov) {
    if (file_exists(__DIR__ . '/pcov_coverage.php')) {
        require_once __DIR__ . '/pcov_coverage.php';
    } else {
        // Tương lai code Fuzzer PCOV sẽ viết ở đây. 
        // pcov_start(); register_shutdown_function(function() { ... lưu file lcov/json })
    }
}

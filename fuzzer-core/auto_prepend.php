<?php
require_once __DIR__ . '/bootstrap/auto_prepend.php';
return;
/**
 * FUZZER ENGINE - Điểm khởi đầu của mọi ứng dụng.
 * Được nạp TỰ ĐỘNG BỞI PHP (thông qua auto_prepend_file trong php.ini).
 * Không được xóa hoặc đổi tên.
 * Cái này là MUST USE plugin
 */

// Lấy tham số cấu hình từ môi trường Docker
$enable_uopz = getenv('FUZZER_ENABLE_UOPZ') === '1';
$enable_pcov = getenv('FUZZER_ENABLE_PCOV') === '1';

// 1. Kích hoạt UOPZ Hooking (Giai đoạn đầu)
if ($enable_uopz) {
    $uopzBootstrap = __DIR__ . '/uopz_hook_v2.php';
    if (file_exists($uopzBootstrap)) {
        require_once $uopzBootstrap;
    }

    // auto_prepend chay truoc WordPress, nen ta dat them 1 MU plugin bootstrap
    // de retry __uopz_install_wp_hooks() khi WP da load xong plugin API.
    $muPluginSource = __DIR__ . '/uopz_mu_plugin.php';
    $muPluginDir    = '/var/www/html/wp-content/mu-plugins';
    $muPluginTarget = $muPluginDir . '/fuzzer-uopz-bootstrap.php';

    if (file_exists($muPluginSource)) {
        if (!is_dir($muPluginDir)) {
            @mkdir($muPluginDir, 0777, true);
        }

        $shouldSyncMuPlugin = !file_exists($muPluginTarget)
            || @md5_file($muPluginSource) !== @md5_file($muPluginTarget);

        if ($shouldSyncMuPlugin) {
            @copy($muPluginSource, $muPluginTarget);
        }
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

<?php
/**
 * Plugin Name: Fuzzer UOPZ Bootstrap
 * Description: Retries UOPZ hook installation after WordPress has loaded its hook API.
 * Author: Fuzz_WP
 * Version: 1.0.0
 */

// auto_prepend da include file instrument chinh o dau request, nhung MU plugin nay
// van require_once lai de truong hop file nay duoc load doc lap trong moi truong khac.
$instrumentationFile = '/var/www/uopz/fuzzer-core/uopz_hook_v2.php';
if (file_exists($instrumentationFile)) {
    require_once $instrumentationFile;
}

if (function_exists('add_action')) {
    // Chay rat som sau khi plugin API san sang, truoc phan lon plugin thong thuong.
    add_action('muplugins_loaded', function () {
        if (function_exists('__uopz_install_wp_hooks')) {
            __uopz_install_wp_hooks();
        }
    }, -99999);

    // Goi them o plugins_loaded de bat cac truong hop muplugins_loaded van con qua som.
    add_action('plugins_loaded', function () {
        if (function_exists('__uopz_install_wp_hooks')) {
            __uopz_install_wp_hooks();
        }
    }, -99999);
}

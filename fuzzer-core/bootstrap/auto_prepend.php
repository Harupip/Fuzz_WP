<?php
/**
 * Fuzzer bootstrap loaded by PHP via auto_prepend_file.
 */

$enable_uopz = getenv('FUZZER_ENABLE_UOPZ') === '1';
$enable_pcov = getenv('FUZZER_ENABLE_PCOV') === '1';

if ($enable_uopz) {
    $uopzBootstrap = dirname(__DIR__) . '/instrumentation/uopz_hook.php';
    if (file_exists($uopzBootstrap)) {
        require_once $uopzBootstrap;
    }

    $muPluginSource = __DIR__ . '/uopz_mu_plugin.php';
    $muPluginDir = '/var/www/html/wp-content/mu-plugins';
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

if ($enable_pcov) {
    $pcovExporter = dirname(__DIR__) . '/instrumentation/pcov_exporter.php';
    if (file_exists($pcovExporter)) {
        require_once $pcovExporter;
    }
}

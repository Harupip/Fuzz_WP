<?php
/**
 * PCOV-based file/line coverage exporter for the target WordPress plugin.
 *
 * Output:
 *   - /var/www/uopz/output/pcov/requests/{request_id}.json
 *   - /var/www/uopz/output/pcov_total_coverage.json
 */

if (!extension_loaded('pcov') || !function_exists('pcov\\start')) {
    return;
}

function __pcov_base_dir(): string
{
    return '/var/www/uopz/output';
}

function __pcov_requests_dir(): string
{
    return __pcov_base_dir() . '/pcov/requests';
}

function __pcov_total_file(): string
{
    return __pcov_base_dir() . '/pcov_total_coverage.json';
}

function __pcov_request_id(): string
{
    if (isset($GLOBALS['__uopz_request']['request_id']) && is_string($GLOBALS['__uopz_request']['request_id'])) {
        return $GLOBALS['__uopz_request']['request_id'];
    }

    return 'pcov_' . date('His') . '_' . bin2hex(random_bytes(4));
}

function __pcov_target_root(): string
{
    static $resolved = null;

    if ($resolved !== null) {
        return $resolved;
    }

    $target = getenv('TARGET_APP_PATH') ?: '/wp-content/plugins/';
    $target = str_replace('\\', '/', trim($target));

    if ($target === '') {
        $target = '/wp-content/plugins/';
    }

    if (!str_starts_with($target, '/var/www/')) {
        $target = '/var/www/html/' . ltrim($target, '/');
    }

    $resolved = rtrim(preg_replace('#/+#', '/', $target), '/');

    return $resolved;
}

function __pcov_relative_path(string $file): string
{
    $targetRoot = __pcov_target_root();
    $normalized = str_replace('\\', '/', $file);

    if (str_starts_with($normalized, $targetRoot . '/')) {
        return substr($normalized, strlen($targetRoot) + 1);
    }

    return basename($normalized);
}

function __pcov_target_files(): array
{
    static $files = null;

    if ($files !== null) {
        return $files;
    }

    $files = [];
    $targetRoot = __pcov_target_root();

    if (!is_dir($targetRoot)) {
        return $files;
    }

    $iterator = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator($targetRoot, FilesystemIterator::SKIP_DOTS)
    );

    foreach ($iterator as $item) {
        if (!$item->isFile()) {
            continue;
        }

        if (strtolower($item->getExtension()) !== 'php') {
            continue;
        }

        $path = str_replace('\\', '/', $item->getPathname());
        $files[$path] = $path;
    }

    ksort($files);

    return $files;
}

function __pcov_executable_lines(string $file): array
{
    static $cache = [];

    if (isset($cache[$file])) {
        return $cache[$file];
    }

    $source = @file_get_contents($file);
    if ($source === false) {
        return $cache[$file] = [];
    }

    $ignored = [
        T_WHITESPACE,
        T_COMMENT,
        T_DOC_COMMENT,
        T_OPEN_TAG,
        T_OPEN_TAG_WITH_ECHO,
        T_CLOSE_TAG,
        T_INLINE_HTML,
    ];

    $lines = [];

    foreach (PhpToken::tokenize($source) as $token) {
        if (in_array($token->id, $ignored, true)) {
            continue;
        }

        $line = $token->line;
        $span = substr_count($token->text, "\n");

        for ($offset = 0; $offset <= $span; $offset++) {
            $lines[$line + $offset] = $line + $offset;
        }
    }

    ksort($lines);

    return $cache[$file] = array_values($lines);
}

function __pcov_percent(int $covered, int $total): string
{
    if ($total <= 0) {
        return '0%';
    }

    return round(($covered / $total) * 100, 2) . '%';
}

function __pcov_write_json_atomic(string $path, array $data): void
{
    $dir = dirname($path);
    if (!is_dir($dir)) {
        @mkdir($dir, 0777, true);
    }

    $tmp = $path . '.tmp.' . bin2hex(random_bytes(4));
    file_put_contents($tmp, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
    rename($tmp, $path);
}

function __pcov_collect_request_report(): array
{
    $rawCoverage = pcov\collect();
    $targetRoot = __pcov_target_root();
    $targetFiles = __pcov_target_files();

    $files = [];
    $coveredFiles = 0;
    $coveredLines = 0;
    $executableLines = 0;

    foreach ($targetFiles as $file) {
        $normalized = str_replace('\\', '/', $file);
        $executedLines = [];

        if (isset($rawCoverage[$normalized]) && is_array($rawCoverage[$normalized])) {
            foreach ($rawCoverage[$normalized] as $line) {
                $line = (int) $line;
                if ($line > 0) {
                    $executedLines[$line] = $line;
                }
            }
        }

        ksort($executedLines);

        $executable = __pcov_executable_lines($normalized);
        $executedCount = count($executedLines);
        $executableCount = count($executable);

        if ($executedCount > 0) {
            $coveredFiles++;
        }

        $coveredLines += $executedCount;
        $executableLines += $executableCount;

        $files[__pcov_relative_path($normalized)] = [
            'absolute_path' => $normalized,
            'executed_lines' => array_values($executedLines),
            'executed_line_count' => $executedCount,
            'executable_line_count' => $executableCount,
            'coverage_percent' => __pcov_percent($executedCount, $executableCount),
        ];
    }

    ksort($files);

    return [
        'request_id' => __pcov_request_id(),
        'timestamp' => date('Y-m-d H:i:s'),
        'target_root' => $targetRoot,
        'summary' => [
            'covered_files' => $coveredFiles,
            'total_files' => count($targetFiles),
            'covered_lines' => $coveredLines,
            'executable_lines' => $executableLines,
            'coverage_percent' => __pcov_percent($coveredLines, $executableLines),
        ],
        'files' => $files,
    ];
}

function __pcov_update_total_report(array $requestReport): void
{
    $totalFile = __pcov_total_file();
    $lockFile = __pcov_base_dir() . '/pcov_total_coverage.lock';

    $lockHandle = fopen($lockFile, 'c+');
    if (!$lockHandle) {
        return;
    }

    if (!flock($lockHandle, LOCK_EX)) {
        fclose($lockHandle);
        return;
    }

    try {
        $existing = [];
        if (file_exists($totalFile)) {
            $existing = json_decode(file_get_contents($totalFile), true) ?? [];
        }

        $files = $existing['data']['files'] ?? [];

        foreach ($requestReport['files'] as $relativePath => $data) {
            $mergedExecuted = [];

            foreach ($files[$relativePath]['executed_lines'] ?? [] as $line) {
                $mergedExecuted[(int) $line] = (int) $line;
            }

            foreach ($data['executed_lines'] as $line) {
                $mergedExecuted[(int) $line] = (int) $line;
            }

            ksort($mergedExecuted);

            $executedCount = count($mergedExecuted);
            $executableCount = (int) ($data['executable_line_count'] ?? 0);

            $files[$relativePath] = [
                'absolute_path' => $data['absolute_path'],
                'executed_lines' => array_values($mergedExecuted),
                'executed_line_count' => $executedCount,
                'executable_line_count' => $executableCount,
                'coverage_percent' => __pcov_percent($executedCount, $executableCount),
            ];
        }

        ksort($files);

        $coveredFiles = 0;
        $coveredLines = 0;
        $executableLines = 0;

        foreach ($files as $data) {
            $coveredLines += (int) ($data['executed_line_count'] ?? 0);
            $executableLines += (int) ($data['executable_line_count'] ?? 0);

            if ((int) ($data['executed_line_count'] ?? 0) > 0) {
                $coveredFiles++;
            }
        }

        $totalReport = [
            'metadata' => [
                'target_root' => $requestReport['target_root'],
                'total_files' => count($files),
                'covered_files' => $coveredFiles,
                'covered_lines' => $coveredLines,
                'executable_lines' => $executableLines,
                'coverage_percent' => __pcov_percent($coveredLines, $executableLines),
                'last_request_id' => $requestReport['request_id'],
                'last_request_time' => $requestReport['timestamp'],
            ],
            'data' => [
                'files' => $files,
            ],
        ];

        __pcov_write_json_atomic($totalFile, $totalReport);
    } finally {
        flock($lockHandle, LOCK_UN);
        fclose($lockHandle);
    }
}

pcov\start();

register_shutdown_function(function (): void {
    $requestReport = __pcov_collect_request_report();
    $requestFile = __pcov_requests_dir() . '/' . $requestReport['request_id'] . '.json';

    __pcov_write_json_atomic($requestFile, $requestReport);
    __pcov_update_total_report($requestReport);

    if (function_exists('pcov\\clear')) {
        pcov\clear();
    }

    if (function_exists('pcov\\stop')) {
        pcov\stop();
    }
});

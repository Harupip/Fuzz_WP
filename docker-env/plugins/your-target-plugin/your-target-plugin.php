<?php
/**
 * Plugin Name: Your Target Plugin (Fuzzer Demo)
 * Description: Dummy plugin mô phỏng thao tác CRUD qua REST API, Thêm bảng DB để Test kỹ thuật Fuzz Hook bằng UOPZ.
 * Version: 1.0.0
 * Author: Fuzzer Researcher
 */

// Đảm bảo không truy cập trực tiếp
if (!defined('ABSPATH')) {
    exit;
}

// --------------------------------------------------------------------------
// 1. CÁC HOOK ĐƯỢC CHẠY KHI WP KHỞI TẠO HOẶC LÀM VIỆC CHUNG
// --------------------------------------------------------------------------

// Tạo bảng DB giả lập khi Activate
register_activation_hook(__FILE__, 'ytp_activate_plugin');
function ytp_activate_plugin() {
    global $wpdb;
    $table_name = $wpdb->prefix . 'ytp_items';
    $sql = "CREATE TABLE IF NOT EXISTS $table_name (
        id int(9) NOT NULL AUTO_INCREMENT,
        item_name varchar(50) NOT NULL,
        UNIQUE KEY id (id)
    );";
    require_once(ABSPATH . 'wp-admin/includes/upgrade.php');
    dbDelta($sql);
    
    // Gọi thử 1 action do plugin tự tạo
    do_action('ytp_plugin_activated');
}

// Filter chạy mỗi khi WordPress hiển thị nội dung bài viết
add_filter('the_content', 'ytp_append_content_marker');
function ytp_append_content_marker($content) {
    if (is_single()) {
        $content .= '<p style="color:red;">[Hook the_content: Fuzzed Context Inject Here]</p>';
    }
    return $content;
}

// --------------------------------------------------------------------------
// 2. TẠO CÁC ENDPOINT REST API (CRUD)
// --------------------------------------------------------------------------

// Đăng ký hook Init API
add_action('rest_api_init', 'ytp_register_api_endpoints');

function ytp_register_api_endpoints() {
    $namespace = 'ytp/v1';

    // GET /wp-json/ytp/v1/items
    register_rest_route($namespace, '/items', array(
        'methods'  => 'GET',
        'callback' => 'ytp_get_items',
        'permission_callback' => '__return_true'
    ));

    // POST /wp-json/ytp/v1/items
    register_rest_route($namespace, '/items', array(
        'methods'  => 'POST',
        'callback' => 'ytp_create_item',
        'permission_callback' => '__return_true'
    ));
}

// Handler cho GET
function ytp_get_items($request) {
    global $wpdb;
    $table_name = $wpdb->prefix . 'ytp_items';
    $results = $wpdb->get_results("SELECT * FROM $table_name", ARRAY_A);
    
    // Test filter do plugin tạo (Sink khả nghi)
    $results = apply_filters('ytp_filter_get_items_results', $results);
    
    return rest_ensure_response(array('success' => true, 'data' => $results));
}

// Handler cho POST (Thêm mới item)
function ytp_create_item($request) {
    $item_name = $request->get_param('name');
    
    if (empty($item_name)) {
        return new WP_Error('missing_param', 'Missname parameter "name"', array('status' => 400));
    }

    global $wpdb;
    $table_name = $wpdb->prefix . 'ytp_items';
    
    // Sink Injection ở đây nếu Fuzzer thử truyền Param "$item_name" có SQLi
    $wpdb->insert($table_name, array('item_name' => $item_name));
    
    // Test action do fuzzer trigger
    do_action('ytp_item_created', $wpdb->insert_id, $item_name);

    return rest_ensure_response(array('success' => true, 'inserted_id' => $wpdb->insert_id));
}

// --------------------------------------------------------------------------
// 3. NHỮNG HOOK ĐƯỢC REGISTER NHƯNG KHÔNG BAO GIỜ TRIGGER (BLINDSPOTS)
// --------------------------------------------------------------------------
// Fuzzer sẽ nhận diện các Action/Filter này thuộc về "Uncovered" vì chưa hề gọi apply_filters/do_action

add_action('ytp_secret_admin_action', function($user_id) {
    // Action nhạy cảm chỉ chạy khi Admin làm gì đó
    error_log("Triggered Secret Admin Action: " . $user_id);
});

add_filter('ytp_process_payment_data', 'ytp_handle_payment');
function ytp_handle_payment($data) {
    // Code nhạy cảm, ít khi trigger
    return urlencode($data) . "_processed";
}

// --------------------------------------------------------------------------
// 4. GIAO DIỆN TEST API (DÀNH CHO NGƯỜI DÙNG TƯƠNG TÁC)
// --------------------------------------------------------------------------
add_action('template_redirect', 'ytp_render_test_ui');
function ytp_render_test_ui() {
    // Nếu có query ?test-api=1, ta sẽ hiển thị trang HTML test thay vì load Theme WP
    if (isset($_GET['test-api']) && $_GET['test-api'] === '1') {
        ?>
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Test API - UOPZ Fuzzer Demo</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; padding: 20px; background: #f0f2f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                h1 { color: #1d2327; border-bottom: 2px solid #2271b1; padding-bottom: 10px; }
                .panel { margin-top: 20px; border: 1px solid #c3c4c7; padding: 15px; border-radius: 4px; background: #f6f7f7; }
                button { background: #2271b1; color: white; border: none; padding: 10px 15px; border-radius: 4px; cursor: pointer; font-weight: bold; }
                button:hover { background: #135e96; }
                pre { background: #1d2327; color: #a9f682; padding: 15px; border-radius: 4px; overflow-x: auto; min-height: 100px; }
                input[type="text"] { padding: 8px; width: 250px; border: 1px solid #8c8f94; border-radius: 4px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔌 WordPress API Test Control Panel</h1>
                <p>Nhấn các nút bên dưới để mô phỏng một Client gọi API của WordPress. Mỗi khi bạn gọi, UOPZ sẽ bắt Hook dưới nền.</p>

                <div class="panel">
                    <h3>1. Xem danh sách Items (Method GET)</h3>
                    <button onclick="getItems()">Call GET /wp-json/ytp/v1/items</button>
                    <pre id="getResponse">Chưa có dữ liệu...</pre>
                </div>

                <div class="panel">
                    <h3>2. Thêm mới Item (Method POST)</h3>
                    <input type="text" id="itemName" placeholder="Nhập tên sản phẩm, VD: iPhone 15">
                    <button onclick="createItem()">Call POST /wp-json/ytp/v1/items</button>
                    <pre id="postResponse">Chưa có thao tác thêm...</pre>
                </div>
                
                <div class="panel">
                    <h3>3. Truy cập xem bài báo cáo tổng hợp</h3>
                    <p>Hãy xem file: <code>UOPZ_demo/docker-env/hook-coverage/total_coverage.json</code> trên máy tính sau khi nhấn các nút trên!</p>
                </div>
            </div>

            <script>
                const BASE_URL = window.location.origin + '/index.php?rest_route=/ytp/v1/items';

                async function getItems() {
                    const resBox = document.getElementById('getResponse');
                    resBox.innerText = 'Đang tải...';
                    try {
                        const response = await fetch(BASE_URL);
                        const json = await response.json();
                        resBox.innerText = JSON.stringify(json, null, 2);
                    } catch (e) {
                        resBox.innerText = "Lỗi: " + e.message;
                    }
                }

                async function createItem() {
                    const resBox = document.getElementById('postResponse');
                    const name = document.getElementById('itemName').value;
                    if (!name) return alert('Vui lòng nhập tên sản phẩm!');
                    
                    resBox.innerText = 'Đang gửi...';
                    try {
                        const response = await fetch(BASE_URL, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                            body: 'name=' + encodeURIComponent(name)
                        });
                        const json = await response.json();
                        resBox.innerText = JSON.stringify(json, null, 2);
                        document.getElementById('itemName').value = '';
                    } catch (e) {
                        resBox.innerText = "Lỗi: " + e.message;
                    }
                }
            </script>
        </body>
        </html>
        <?php
        exit; // Kết thúc request tại đây, không load giao diện WP nữa
    }
}


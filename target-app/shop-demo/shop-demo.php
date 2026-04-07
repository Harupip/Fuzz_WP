<?php
/**
 * Plugin Name: Shop Demo
 * Description: WordPress e-commerce demo - CRUD Products and Orders via REST API for UOPZ hook coverage.
 * Version: 1.0.0
 * Author: LVTS Researcher
 */

if (!defined('ABSPATH')) exit;

// ============================================================================
// 1. DATABASE SETUP
// ============================================================================

register_activation_hook(__FILE__, 'shop_activate');
function shop_activate() {
    global $wpdb;
    $charset = $wpdb->get_charset_collate();

    $wpdb->query("CREATE TABLE IF NOT EXISTS {$wpdb->prefix}shop_products (
        id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
        name        VARCHAR(200) NOT NULL,
        description TEXT,
        price       DECIMAL(10,2) NOT NULL DEFAULT 0,
        stock       INT NOT NULL DEFAULT 0,
        created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id)
    ) $charset;");

    $wpdb->query("CREATE TABLE IF NOT EXISTS {$wpdb->prefix}shop_orders (
        id           INT UNSIGNED NOT NULL AUTO_INCREMENT,
        product_id   INT UNSIGNED NOT NULL,
        quantity     INT NOT NULL DEFAULT 1,
        total_price  DECIMAL(10,2) NOT NULL,
        customer     VARCHAR(200) NOT NULL,
        status       VARCHAR(50) NOT NULL DEFAULT 'pending',
        created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id)
    ) $charset;");

    do_action('shop_plugin_activated');
}

// ============================================================================
// 2. HOOKS DANG KY
// ============================================================================

add_filter('the_content', 'shop_append_promo_banner');
function shop_append_promo_banner($content) {
    if (is_single()) {
        $content .= '<p style="background:#f0f4ff;padding:10px;border-radius:6px">[Shop Demo] Xem san pham moi nhat!</p>';
    }
    return $content;
}

add_action('rest_api_init', 'shop_register_endpoints');

add_action('shop_product_created', function($id, $data) {
    error_log('shop_product_created fired: ' . $id);
}, 10, 2);

// ============================================================================
// 3. REST API - CRUD Products & Orders
// ============================================================================

function shop_register_endpoints() {
    $ns = 'shop/v1';

    register_rest_route($ns, '/products', [
        ['methods' => 'GET',  'callback' => 'shop_get_products',   'permission_callback' => '__return_true'],
        ['methods' => 'POST', 'callback' => 'shop_create_product', 'permission_callback' => '__return_true'],
    ]);

    register_rest_route($ns, '/products/(?P<id>\d+)', [
        ['methods' => 'GET',    'callback' => 'shop_get_product',    'permission_callback' => '__return_true'],
        ['methods' => 'PUT',    'callback' => 'shop_update_product', 'permission_callback' => '__return_true'],
        ['methods' => 'DELETE', 'callback' => 'shop_delete_product', 'permission_callback' => '__return_true'],
    ]);

    register_rest_route($ns, '/orders', [
        ['methods' => 'GET',  'callback' => 'shop_get_orders',   'permission_callback' => '__return_true'],
        ['methods' => 'POST', 'callback' => 'shop_create_order', 'permission_callback' => '__return_true'],
    ]);

    register_rest_route($ns, '/hooks/lab', [
        ['methods' => 'POST', 'callback' => 'shop_run_hook_lab', 'permission_callback' => '__return_true'],
    ]);
}

function shop_get_products($req) {
    global $wpdb;
    $results = $wpdb->get_results("SELECT * FROM {$wpdb->prefix}shop_products ORDER BY id DESC", ARRAY_A);
    $results = apply_filters('shop_filter_products_list', $results);
    return rest_ensure_response(['success' => true, 'count' => count($results), 'data' => $results]);
}

function shop_get_product($req) {
    global $wpdb;
    $id  = (int) $req['id'];
    $row = $wpdb->get_row($wpdb->prepare("SELECT * FROM {$wpdb->prefix}shop_products WHERE id=%d", $id), ARRAY_A);
    if (!$row) return new WP_Error('not_found', 'Product not found', ['status' => 404]);
    $row = apply_filters('shop_filter_single_product', $row, $id);
    return rest_ensure_response(['success' => true, 'data' => $row]);
}

function shop_create_product($req) {
    global $wpdb;
    $name  = sanitize_text_field($req->get_param('name') ?? '');
    $desc  = sanitize_textarea_field($req->get_param('description') ?? '');
    $price = (float)($req->get_param('price') ?? 0);
    $stock = (int)($req->get_param('stock')   ?? 0);

    if (empty($name)) return new WP_Error('missing_name', 'Truong "name" la bat buoc', ['status' => 400]);

    $data = apply_filters('shop_before_create_product', compact('name', 'desc', 'price', 'stock'));

    $wpdb->insert("{$wpdb->prefix}shop_products", [
        'name'        => $data['name'],
        'description' => $data['desc'],
        'price'       => $data['price'],
        'stock'       => $data['stock'],
    ]);
    $id = $wpdb->insert_id;
    do_action('shop_product_created', $id, $data);
    return rest_ensure_response(['success' => true, 'inserted_id' => $id]);
}

function shop_update_product($req) {
    global $wpdb;
    $id = (int) $req['id'];
    $fields = [];
    if ($req->get_param('name')        !== null) $fields['name']        = sanitize_text_field($req->get_param('name'));
    if ($req->get_param('description') !== null) $fields['description'] = sanitize_textarea_field($req->get_param('description'));
    if ($req->get_param('price')       !== null) $fields['price']       = (float) $req->get_param('price');
    if ($req->get_param('stock')       !== null) $fields['stock']       = (int) $req->get_param('stock');
    if (empty($fields)) return new WP_Error('no_fields', 'Khong co truong nao de cap nhat', ['status' => 400]);
    $fields   = apply_filters('shop_before_update_product', $fields, $id);
    $updated  = $wpdb->update("{$wpdb->prefix}shop_products", $fields, ['id' => $id]);
    if ($updated === false) return new WP_Error('db_error', 'Loi database', ['status' => 500]);
    do_action('shop_product_updated', $id, $fields);
    return rest_ensure_response(['success' => true, 'updated_id' => $id]);
}

function shop_delete_product($req) {
    global $wpdb;
    $id = (int) $req['id'];
    do_action('shop_before_delete_product', $id);
    $deleted = $wpdb->delete("{$wpdb->prefix}shop_products", ['id' => $id]);
    if (!$deleted) return new WP_Error('not_found', 'Khong tim thay san pham', ['status' => 404]);
    do_action('shop_product_deleted', $id);
    return rest_ensure_response(['success' => true, 'deleted_id' => $id]);
}

function shop_get_orders($req) {
    global $wpdb;
    $results = $wpdb->get_results("SELECT * FROM {$wpdb->prefix}shop_orders ORDER BY id DESC", ARRAY_A);
    $results = apply_filters('shop_filter_orders_list', $results);
    return rest_ensure_response(['success' => true, 'count' => count($results), 'data' => $results]);
}

function shop_create_order($req) {
    global $wpdb;
    $pid      = (int) ($req->get_param('product_id') ?? 0);
    $qty      = (int) ($req->get_param('quantity')   ?? 1);
    $customer = sanitize_text_field($req->get_param('customer') ?? '');
    if (!$pid || empty($customer)) return new WP_Error('missing_params', 'Can "product_id" va "customer"', ['status' => 400]);
    $product = $wpdb->get_row($wpdb->prepare("SELECT * FROM {$wpdb->prefix}shop_products WHERE id=%d", $pid), ARRAY_A);
    if (!$product) return new WP_Error('not_found', 'Khong tim thay san pham', ['status' => 404]);
    $total = apply_filters('shop_calculate_order_total', $product['price'] * $qty, $pid, $qty);
    $wpdb->insert("{$wpdb->prefix}shop_orders", [
        'product_id'  => $pid,
        'quantity'    => $qty,
        'total_price' => $total,
        'customer'    => $customer,
        'status'      => 'pending',
    ]);
    $order_id = $wpdb->insert_id;
    do_action('shop_order_placed', $order_id, $product, $qty, $customer);
    return rest_ensure_response(['success' => true, 'order_id' => $order_id, 'total_price' => $total]);
}

function shop_run_hook_lab($req) {
    $trace = [];
    $action_tag = 'shop_demo_runtime_action';
    $filter_tag = 'shop_demo_runtime_filter';

    $all_listener = function() use (&$trace) {
        $args = func_get_args();
        $trace[] = [
            'api'  => 'all',
            'hook' => (string) ($args[0] ?? 'unknown'),
            'note' => 'Listener on "all" observed this hook call',
        ];
    };

    $action_early = function($payload) use (&$trace, $action_tag) {
        $trace[] = [
            'api'     => 'do_action',
            'hook'    => $action_tag,
            'handler' => 'action_priority_5',
            'payload' => $payload,
        ];
    };

    $action_late = function($payload) use (&$trace, $action_tag) {
        $trace[] = [
            'api'     => 'do_action',
            'hook'    => $action_tag,
            'handler' => 'action_priority_20',
            'payload' => $payload,
        ];
    };

    $filter_primary = function($payload, $context) use (&$trace, $filter_tag) {
        $payload['sequence'][] = 'filter_priority_10';
        $payload['label'] .= '|f10';
        $payload['context'][] = $context;
        $trace[] = [
            'api'     => 'apply_filters',
            'hook'    => $filter_tag,
            'handler' => 'filter_priority_10',
            'payload' => $payload,
        ];
        return $payload;
    };

    $filter_secondary = function($payload, $context) use (&$trace, $filter_tag) {
        $payload['sequence'][] = 'filter_priority_30';
        $payload['label'] .= '|f30';
        $payload['context'][] = strtoupper($context);
        $trace[] = [
            'api'     => 'apply_filters',
            'hook'    => $filter_tag,
            'handler' => 'filter_priority_30',
            'payload' => $payload,
        ];
        return $payload;
    };

    add_filter('all', $all_listener, 1, PHP_INT_MAX);
    $trace[] = ['api' => 'add_filter', 'hook' => 'all', 'handler' => 'all_listener', 'priority' => 1];

    add_action($action_tag, $action_early, 5, 1);
    $trace[] = ['api' => 'add_action', 'hook' => $action_tag, 'handler' => 'action_priority_5', 'priority' => 5];

    add_action($action_tag, $action_late, 20, 1);
    $trace[] = ['api' => 'add_action', 'hook' => $action_tag, 'handler' => 'action_priority_20', 'priority' => 20];

    add_filter($filter_tag, $filter_primary, 10, 2);
    $trace[] = ['api' => 'add_filter', 'hook' => $filter_tag, 'handler' => 'filter_priority_10', 'priority' => 10];

    add_filter($filter_tag, $filter_secondary, 30, 2);
    $trace[] = ['api' => 'add_filter', 'hook' => $filter_tag, 'handler' => 'filter_priority_30', 'priority' => 30];

    do_action($action_tag, ['stage' => 'before_remove']);

    $filtered_before_remove = apply_filters($filter_tag, [
        'label'    => 'seed',
        'sequence' => [],
        'context'  => [],
    ], 'before_remove');

    $removed_action = remove_action($action_tag, $action_late, 20);
    $trace[] = ['api' => 'remove_action', 'hook' => $action_tag, 'handler' => 'action_priority_20', 'removed' => $removed_action];

    $removed_filter = remove_filter($filter_tag, $filter_secondary, 30);
    $trace[] = ['api' => 'remove_filter', 'hook' => $filter_tag, 'handler' => 'filter_priority_30', 'removed' => $removed_filter];

    do_action($action_tag, ['stage' => 'after_remove']);

    $filtered_after_remove = apply_filters($filter_tag, [
        'label'    => 'seed',
        'sequence' => [],
        'context'  => [],
    ], 'after_remove');

    $removed_all = remove_filter('all', $all_listener, 1);
    $trace[] = ['api' => 'remove_filter', 'hook' => 'all', 'handler' => 'all_listener', 'removed' => $removed_all];

    do_action($action_tag, ['stage' => 'after_all_removed']);

    return rest_ensure_response([
        'success' => true,
        'summary' => [
            'action_order_before_remove' => ['action_priority_5', 'action_priority_20'],
            'action_order_after_remove'  => ['action_priority_5'],
            'filter_order_before_remove' => $filtered_before_remove['sequence'],
            'filter_order_after_remove'  => $filtered_after_remove['sequence'],
            'all_listener_active_until'  => 'remove_filter("all", ...)',
        ],
        'results' => [
            'filtered_before_remove' => $filtered_before_remove,
            'filtered_after_remove'  => $filtered_after_remove,
        ],
        'trace' => $trace,
    ]);
}

// ============================================================================
// 4. BLINDSPOT HOOKS - Dang ky nhung KHONG BAO GIO duoc trigger
//    UOPZ se ghi day vao "blindspots" (attack surface tiem nang)
// ============================================================================

add_action('shop_secret_admin_export', function($user_id) {
    error_log("[SHOP] Admin export by: $user_id");
});

add_filter('shop_process_refund', function($order_id) {
    return ['status' => 'refunded', 'order_id' => $order_id];
});

add_action('shop_send_invoice_email', function($order_id, $email) {
    // Chua implement
}, 10, 2);

// ============================================================================
// 5. TEST UI - Giao dien tai /?test-shop=1
// ============================================================================

add_action('template_redirect', 'shop_render_test_ui');
function shop_render_test_ui() {
    if (!isset($_GET['test-shop']) || $_GET['test-shop'] !== '1') return;
    ?>
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Shop Demo - API Control Panel</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',sans-serif;background:#0f1117;color:#e2e8f0;min-height:100vh}
.header{background:linear-gradient(135deg,#1e293b,#0f172a);border-bottom:1px solid #1e3a5f;padding:24px 40px;display:flex;align-items:center;gap:16px}
.header h1{font-size:22px;font-weight:700;color:#fff}
.badge{padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;letter-spacing:.5px}
.badge-api{background:#0ea5e9;color:#fff}
.badge-uopz{background:#7c3aed;color:#fff}
.main{max-width:1100px;margin:0 auto;padding:32px 20px;display:grid;grid-template-columns:1fr 1fr;gap:20px}
.card{background:#1e293b;border:1px solid #2d3f55;border-radius:12px;overflow:hidden}
.card-header{padding:16px 20px;border-bottom:1px solid #2d3f55;display:flex;align-items:center;gap:10px}
.card-header h2{font-size:14px;font-weight:600;color:#94a3b8}
.method{padding:3px 8px;border-radius:5px;font-size:11px;font-weight:700;font-family:'JetBrains Mono',monospace}
.GET{background:#064e3b;color:#34d399}.POST{background:#1e3a8a;color:#60a5fa}
.PUT{background:#78350f;color:#fbbf24}.DELETE{background:#7f1d1d;color:#f87171}
.card-body{padding:20px}
.form-row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
input{font-family:'Inter',sans-serif;font-size:13px;padding:8px 12px;background:#0f172a;border:1px solid #334155;border-radius:7px;color:#e2e8f0;outline:none}
input:focus{border-color:#0ea5e9}
input.w-full{width:100%}
input.w-sm{width:120px}
button{padding:9px 18px;border:none;border-radius:7px;font-family:'Inter',sans-serif;font-size:13px;font-weight:600;cursor:pointer;transition:all .2s;white-space:nowrap}
.btn-get{background:#059669;color:#fff}.btn-get:hover{background:#047857}
.btn-post{background:#2563eb;color:#fff}.btn-post:hover{background:#1d4ed8}
.btn-put{background:#d97706;color:#fff}.btn-put:hover{background:#b45309}
.btn-del{background:#dc2626;color:#fff}.btn-del:hover{background:#b91c1c}
pre{background:#0a0e1a;border:1px solid #1e3a5f;border-radius:8px;padding:14px;font-family:'JetBrains Mono',monospace;font-size:12px;line-height:1.6;max-height:200px;overflow-y:auto;color:#a5f3fc;white-space:pre-wrap;word-break:break-word;margin-top:12px}
.status-bar{display:flex;align-items:center;gap:8px;margin-top:8px;font-size:12px;color:#64748b}
.dot{width:8px;height:8px;border-radius:50%;background:#334155;transition:all .3s}
.dot.ok{background:#22c55e;box-shadow:0 0 6px #22c55e}
.dot.err{background:#ef4444;box-shadow:0 0 6px #ef4444}
.dot.loading{background:#f59e0b;animation:pulse 1s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.full-width{grid-column:1/-1}
.info-box{background:#1a0e2e;border:1px solid #4c1d95;border-radius:12px;padding:20px;grid-column:1/-1}
.info-box h3{color:#a78bfa;font-size:14px;margin-bottom:10px}
.info-box p{font-size:13px;color:#94a3b8;line-height:1.7}
.main{grid-template-columns:1fr}
.scenario-card,.guide-card,.order-card{display:block}
.card:not(.scenario-card):not(.guide-card):not(.order-card){display:none}
.hero{display:flex;flex-direction:column;gap:14px}
.hero p{font-size:14px;line-height:1.7;color:#94a3b8}
.quick-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.quick-item{background:#0f172a;border:1px solid #334155;border-radius:10px;padding:14px}
.quick-item h3{font-size:13px;color:#f8fafc;margin-bottom:8px}
.quick-item p{font-size:12px;color:#94a3b8;line-height:1.6;margin-bottom:12px}
.btn-run{background:linear-gradient(135deg,#0ea5e9,#2563eb);color:#fff;min-width:240px}
.btn-run:hover{filter:brightness(1.08)}
.api-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}
.api-item{background:#0f172a;border:1px solid #334155;border-radius:10px;padding:14px}
.api-item strong{display:block;color:#e2e8f0;margin-bottom:6px;font-size:13px}
.api-item span{display:block;color:#94a3b8;font-size:12px;line-height:1.6}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}
.step{background:#0f172a;border:1px solid #334155;border-radius:10px;padding:14px}
.step h4{font-size:13px;color:#f8fafc;margin-bottom:8px}
.step p{font-size:12px;color:#94a3b8;line-height:1.65}
.muted{color:#94a3b8;font-size:12px;line-height:1.7}
@media (max-width: 860px){.main{grid-template-columns:1fr}.header{padding:20px}.btn-run{width:100%}}
code{background:#0f172a;padding:2px 6px;border-radius:4px;font-family:'JetBrains Mono',monospace;color:#c4b5fd;font-size:12px}
</style>
</head>
<body>
<div class="header">
  <h1>🛍️ Shop Demo</h1>
  <span class="badge badge-api">REST API</span>
  <span class="badge badge-uopz">UOPZ Active</span>
</div>
<div class="main">

  <div class="card scenario-card">
    <div class="card-header"><span class="method POST">RUN</span><h2>Moi API mot nut, khong can input</h2></div>
    <div class="card-body">
      <div class="hero">
        <p>Moi API ben duoi co nut rieng de bam phat la goi luon. Cac API can <code>product_id</code> se tu dung san pham moi nhat da tao; neu chua co, UI se tu tao san pham mau truoc khi goi.</p>
      </div>
      <div class="quick-grid">
        <div class="quick-item"><h3>GET /products</h3><p>Lay danh sach san pham hien tai.</p><button class="btn-get" onclick="runApiGetProducts()">Lay products</button></div>
        <div class="quick-item"><h3>POST /products</h3><p>Tao san pham mau va cap nhat state local.</p><button class="btn-post" onclick="runApiCreateProduct()">Tao product</button></div>
        <div class="quick-item"><h3>GET /products/{id}</h3><p>Lay san pham moi nhat, tu tao neu chua co.</p><button class="btn-get" onclick="runApiGetProduct()">Lay product theo id</button></div>
        <div class="quick-item"><h3>PUT /products/{id}</h3><p>Cap nhat san pham moi nhat bang du lieu mac dinh.</p><button class="btn-put" onclick="runApiUpdateProduct()">Cap nhat product</button></div>
        <div class="quick-item"><h3>DELETE /products/{id}</h3><p>Xoa san pham moi nhat va reset state local.</p><button class="btn-del" onclick="runApiDeleteProduct()">Xoa product</button></div>
        <div class="quick-item"><h3>GET /orders</h3><p>Lay danh sach don hang hien tai.</p><button class="btn-get" onclick="runApiGetOrders()">Lay orders</button></div>
        <div class="quick-item"><h3>POST /orders</h3><p>Tao order mau cho san pham moi nhat.</p><button class="btn-post" onclick="runApiCreateOrder()">Tao order</button></div>
        <div class="quick-item"><h3>POST /hooks/lab</h3><p>Chay <code>add_action</code>, <code>do_action</code>, <code>apply_filters</code>, <code>remove_*</code> va <code>all</code>.</p><button class="btn-run" onclick="runApiHookLab()">Chay hook lab</button></div>
      </div>
      <div style="margin-top:14px"><button class="btn-run" onclick="runFullScenario()">Chay full scenario</button></div>
      <div class="status-bar"><div class="dot" id="d-run"></div><span id="s-run">Chua gui</span></div>
      <pre id="r-run">-</pre>
    </div>
  </div>

  <div class="card guide-card">
    <div class="card-header"><span class="method GET">MAP</span><h2>Cac API duoc goi trong scenario</h2></div>
    <div class="card-body">
      <div class="api-list">
        <div class="api-item"><strong>POST /products</strong><span>Tao san pham mac dinh va luu <code>lastProductId</code> de cac nut phu thuoc dung lai.</span></div>
        <div class="api-item"><strong>GET /products</strong><span>Lay danh sach san pham, khong phu thuoc state.</span></div>
        <div class="api-item"><strong>GET /products/{id}</strong><span>Dung <code>lastProductId</code>; neu chua co thi UI tu tao san pham mau.</span></div>
        <div class="api-item"><strong>PUT /products/{id}</strong><span>Cap nhat san pham moi nhat va trigger <code>shop_before_update_product</code>.</span></div>
        <div class="api-item"><strong>POST /orders</strong><span>Tao order cho san pham moi nhat va trigger <code>shop_calculate_order_total</code>.</span></div>
        <div class="api-item"><strong>GET /orders</strong><span>Lay danh sach orders hien tai.</span></div>
        <div class="api-item"><strong>POST /hooks/lab</strong><span>Chay phan hook runtime rieng de test <code>add/remove</code>, <code>apply_filters</code>, <code>do_action</code>, <code>all</code>.</span></div>
        <div class="api-item"><strong>DELETE /products/{id}</strong><span>Xoa san pham moi nhat va reset state tren giao dien.</span></div>
      </div>
    </div>
  </div>

  <div class="card order-card">
    <div class="card-header"><span class="method GET">ORDER</span><h2>Thu tu anh huong hook trong /hooks/lab</h2></div>
    <div class="card-body">
      <div class="steps">
        <div class="step"><h4>A. Dang ky runtime</h4><p><code>add_action</code> dang ky 2 callback voi priority 5 va 20. <code>add_filter</code> dang ky 2 filter voi priority 10 va 30. Listener <code>all</code> duoc dang ky dau tien de nghe moi hook.</p></div>
        <div class="step"><h4>B. Lan goi dau</h4><p><code>do_action</code> se chay callback priority 5 truoc 20. <code>apply_filters</code> se bien doi payload theo thu tu 10 truoc 30. Listener <code>all</code> nhin thay ca hai hook nay.</p></div>
        <div class="step"><h4>C. Sau remove</h4><p><code>remove_action</code> bo callback priority 20, <code>remove_filter</code> bo filter priority 30. Lan goi tiep theo chi con callback/filter con lai.</p></div>
        <div class="step"><h4>D. Sau khi bo all</h4><p><code>remove_filter('all', ...)</code> tat listener tong. Hook van chay binh thuong, nhung trace tu listener <code>all</code> se khong con duoc ghi them.</p></div>
      </div>
      <p class="muted">Ban co the doi chieu <code>trace</code> va <code>summary</code> tra ve tu <code>/hooks/lab</code> de xem priority va anh huong cua remove co trung voi coverage/energy hay khong.</p>
    </div>
  </div>

  <div class="card">
    <div class="card-header"><span class="method GET">GET</span><h2>/wp-json/shop/v1/products</h2></div>
    <div class="card-body">
      <button class="btn-get" onclick="call('GET','/products','r1',null,1)">Lay danh sach san pham</button>
      <div class="status-bar"><div class="dot" id="d1"></div><span id="s1">Chua gui</span></div>
      <pre id="r1">-</pre>
    </div>
  </div>

  <div class="card">
    <div class="card-header"><span class="method POST">POST</span><h2>/wp-json/shop/v1/products</h2></div>
    <div class="card-body">
      <div class="form-row"><input id="p_name" placeholder="Ten san pham *" class="w-full"><input id="p_desc" placeholder="Mo ta" class="w-full"></div>
      <div class="form-row"><input id="p_price" placeholder="Gia (VD: 999)" class="w-sm"><input id="p_stock" placeholder="Ton kho" class="w-sm"><button class="btn-post" onclick="createProduct()">Tao san pham</button></div>
      <div class="status-bar"><div class="dot" id="d2"></div><span id="s2">Chua gui</span></div>
      <pre id="r2">-</pre>
    </div>
  </div>

  <div class="card">
    <div class="card-header"><span class="method GET">GET</span><h2>/wp-json/shop/v1/products/{id}</h2></div>
    <div class="card-body">
      <div class="form-row"><input id="g_id" placeholder="Product ID" class="w-sm"><button class="btn-get" onclick="call('GET','/products/'+v('g_id'),'r3',null,3)">Xem san pham</button></div>
      <div class="status-bar"><div class="dot" id="d3"></div><span id="s3">Chua gui</span></div>
      <pre id="r3">-</pre>
    </div>
  </div>

  <div class="card">
    <div class="card-header"><span class="method PUT">PUT</span><h2>/wp-json/shop/v1/products/{id}</h2></div>
    <div class="card-body">
      <div class="form-row"><input id="u_id" placeholder="ID can cap nhat" class="w-sm"><input id="u_name" placeholder="Ten moi" class="w-full"><input id="u_price" placeholder="Gia moi" class="w-sm"></div>
      <button class="btn-put" onclick="updateProduct()">Cap nhat</button>
      <div class="status-bar"><div class="dot" id="d4"></div><span id="s4">Chua gui</span></div>
      <pre id="r4">-</pre>
    </div>
  </div>

  <div class="card">
    <div class="card-header"><span class="method DELETE">DELETE</span><h2>/wp-json/shop/v1/products/{id}</h2></div>
    <div class="card-body">
      <div class="form-row"><input id="del_id" placeholder="Product ID can xoa" class="w-sm"><button class="btn-del" onclick="call('DELETE','/products/'+v('del_id'),'r5',null,5)">Xoa san pham</button></div>
      <div class="status-bar"><div class="dot" id="d5"></div><span id="s5">Chua gui</span></div>
      <pre id="r5">-</pre>
    </div>
  </div>

  <div class="card">
    <div class="card-header"><span class="method POST">POST</span><h2>/wp-json/shop/v1/orders</h2></div>
    <div class="card-body">
      <div class="form-row"><input id="o_pid" placeholder="Product ID *" class="w-sm"><input id="o_qty" placeholder="So luong" class="w-sm"><input id="o_cust" placeholder="Ten khach hang *" class="w-full"></div>
      <button class="btn-post" onclick="createOrder()">Dat hang</button>
      <div class="status-bar"><div class="dot" id="d6"></div><span id="s6">Chua gui</span></div>
      <pre id="r6">-</pre>
    </div>
  </div>

  <div class="card full-width">
    <div class="card-header"><span class="method GET">GET</span><h2>/wp-json/shop/v1/orders</h2></div>
    <div class="card-body">
      <button class="btn-get" onclick="call('GET','/orders','r7',null,7)">Xem tat ca don hang</button>
      <div class="status-bar"><div class="dot" id="d7"></div><span id="s7">Chua gui</span></div>
      <pre id="r7">-</pre>
    </div>
  </div>

  <div class="info-box">
    <h3>UOPZ Hook Instrumentation</h3>
    <p>Moi lan ban nhan nut tren, <strong>UOPZ</strong> tu dong bat toan bo luong hook WordPress va ghi vao:<br>
    - <code>hook-coverage/requests/{request_id}.json</code> — Chi tiet tung request<br>
    - <code>hook-coverage/total_coverage.json</code> — Tong hop coverage tat ca request</p>
  </div>
</div>

<script>
const BASE = window.location.origin + '/index.php?rest_route=/shop/v1';
const v = id => (document.getElementById(id)||{}).value||'';

function setStatus(n, state, msg) {
  const d = document.getElementById('d'+n), s = document.getElementById('s'+n);
  if(d) d.className = 'dot '+state;
  if(s) s.textContent = msg;
}

function setRunStatus(state, msg) {
  const d = document.getElementById('d-run'), s = document.getElementById('s-run');
  if (d) d.className = 'dot ' + state;
  if (s) s.textContent = msg;
}

async function fetchJson(method, path, body) {
  const opts = {method, headers:{}};
  if (body) {
    opts.headers['Content-Type'] = 'application/x-www-form-urlencoded';
    opts.body = body;
  }

  const res = await fetch(BASE + path, opts);
  let text = await res.text();

  if (text.includes('<!DOCTYPE html>')) {
    text = text.substring(0, text.indexOf('<!DOCTYPE html>'));
  }

  const json = JSON.parse(text);
  if (!res.ok) {
    throw new Error((json && json.message) ? json.message : ('HTTP ' + res.status));
  }
  return json;
}

const demoState = {
  lastProductId: null
};

function defaultProductSeed() {
  return {
    name: 'Coverage Demo Product',
    description: 'Auto-generated for hook coverage and energy testing',
    price: '199.50',
    stock: '7'
  };
}

async function ensureProductId() {
  if (demoState.lastProductId) {
    return demoState.lastProductId;
  }

  const created = await fetchJson('POST', '/products', new URLSearchParams(defaultProductSeed()).toString());
  demoState.lastProductId = created.inserted_id;
  return demoState.lastProductId;
}

function renderRunResult(title, payload) {
  const logNode = document.getElementById('r-run');
  logNode.textContent = JSON.stringify({
    title,
    lastProductId: demoState.lastProductId,
    payload
  }, null, 2);
}

async function runApiGetProducts() {
  setRunStatus('loading', 'Dang goi GET /products...');
  try {
    const json = await fetchJson('GET', '/products');
    renderRunResult('GET /products', json);
    setRunStatus('ok', 'GET /products OK');
  } catch (e) {
    renderRunResult('GET /products', {error: e.message});
    setRunStatus('err', 'GET /products loi');
  }
}

async function runApiCreateProduct() {
  setRunStatus('loading', 'Dang goi POST /products...');
  try {
    const json = await fetchJson('POST', '/products', new URLSearchParams(defaultProductSeed()).toString());
    demoState.lastProductId = json.inserted_id;
    renderRunResult('POST /products', json);
    setRunStatus('ok', 'POST /products OK');
  } catch (e) {
    renderRunResult('POST /products', {error: e.message});
    setRunStatus('err', 'POST /products loi');
  }
}

async function runApiGetProduct() {
  setRunStatus('loading', 'Dang goi GET /products/{id}...');
  try {
    const productId = await ensureProductId();
    const json = await fetchJson('GET', '/products/' + productId);
    renderRunResult('GET /products/{id}', {productId, response: json});
    setRunStatus('ok', 'GET /products/{id} OK');
  } catch (e) {
    renderRunResult('GET /products/{id}', {error: e.message});
    setRunStatus('err', 'GET /products/{id} loi');
  }
}

async function runApiUpdateProduct() {
  setRunStatus('loading', 'Dang goi PUT /products/{id}...');
  try {
    const productId = await ensureProductId();
    const json = await fetchJson('PUT', '/products/' + productId, new URLSearchParams({
      name: 'Coverage Demo Product Updated',
      price: '249.75',
      stock: '9'
    }).toString());
    renderRunResult('PUT /products/{id}', {productId, response: json});
    setRunStatus('ok', 'PUT /products/{id} OK');
  } catch (e) {
    renderRunResult('PUT /products/{id}', {error: e.message});
    setRunStatus('err', 'PUT /products/{id} loi');
  }
}

async function runApiDeleteProduct() {
  setRunStatus('loading', 'Dang goi DELETE /products/{id}...');
  try {
    const productId = await ensureProductId();
    const json = await fetchJson('DELETE', '/products/' + productId);
    demoState.lastProductId = null;
    renderRunResult('DELETE /products/{id}', {productId, response: json});
    setRunStatus('ok', 'DELETE /products/{id} OK');
  } catch (e) {
    renderRunResult('DELETE /products/{id}', {error: e.message});
    setRunStatus('err', 'DELETE /products/{id} loi');
  }
}

async function runApiGetOrders() {
  setRunStatus('loading', 'Dang goi GET /orders...');
  try {
    const json = await fetchJson('GET', '/orders');
    renderRunResult('GET /orders', json);
    setRunStatus('ok', 'GET /orders OK');
  } catch (e) {
    renderRunResult('GET /orders', {error: e.message});
    setRunStatus('err', 'GET /orders loi');
  }
}

async function runApiCreateOrder() {
  setRunStatus('loading', 'Dang goi POST /orders...');
  try {
    const productId = await ensureProductId();
    const json = await fetchJson('POST', '/orders', new URLSearchParams({
      product_id: String(productId),
      quantity: '2',
      customer: 'Coverage Runner'
    }).toString());
    renderRunResult('POST /orders', {productId, response: json});
    setRunStatus('ok', 'POST /orders OK');
  } catch (e) {
    renderRunResult('POST /orders', {error: e.message});
    setRunStatus('err', 'POST /orders loi');
  }
}

async function runApiHookLab() {
  setRunStatus('loading', 'Dang goi POST /hooks/lab...');
  try {
    const json = await fetchJson('POST', '/hooks/lab', new URLSearchParams({scenario: 'single'}).toString());
    renderRunResult('POST /hooks/lab', json);
    setRunStatus('ok', 'POST /hooks/lab OK');
  } catch (e) {
    renderRunResult('POST /hooks/lab', {error: e.message});
    setRunStatus('err', 'POST /hooks/lab loi');
  }
}

async function runFullScenario() {
  const logNode = document.getElementById('r-run');
  const log = [];
  const productSeed = defaultProductSeed();
  let productId = null;

  setRunStatus('loading', 'Dang chay scenario...');
  logNode.textContent = 'Dang tao request chain...';

  try {
    const created = await fetchJson('POST', '/products', new URLSearchParams(productSeed).toString());
    productId = created.inserted_id;
    demoState.lastProductId = productId;
    log.push({step: 1, api: 'POST /products', response: created});

    const products = await fetchJson('GET', '/products');
    log.push({step: 2, api: 'GET /products', response: products});

    const single = await fetchJson('GET', '/products/' + productId);
    log.push({step: 3, api: 'GET /products/{id}', response: single});

    const updated = await fetchJson('PUT', '/products/' + productId, new URLSearchParams({
      name: 'Coverage Demo Product Updated',
      price: '249.75',
      stock: '9'
    }).toString());
    log.push({step: 4, api: 'PUT /products/{id}', response: updated});

    const order = await fetchJson('POST', '/orders', new URLSearchParams({
      product_id: String(productId),
      quantity: '2',
      customer: 'Coverage Runner'
    }).toString());
    log.push({step: 5, api: 'POST /orders', response: order});

    const orders = await fetchJson('GET', '/orders');
    log.push({step: 6, api: 'GET /orders', response: orders});

    const hooks = await fetchJson('POST', '/hooks/lab', new URLSearchParams({scenario: 'full'}).toString());
    log.push({step: 7, api: 'POST /hooks/lab', response: hooks});

    const deleted = await fetchJson('DELETE', '/products/' + productId);
    demoState.lastProductId = null;
    log.push({step: 8, api: 'DELETE /products/{id}', response: deleted});

    logNode.textContent = JSON.stringify({
      success: true,
      product_id: productId,
      execution_order: log.map(item => item.api),
      log
    }, null, 2);
    setRunStatus('ok', 'Scenario hoan tat');
  } catch (e) {
    logNode.textContent = JSON.stringify({
      success: false,
      error: e.message,
      product_id: productId,
      log
    }, null, 2);
    setRunStatus('err', 'Scenario that bai');
  }
}

async function call(method, path, resId, body, n) {
  const pre = document.getElementById(resId);
  setStatus(n,'loading','Dang gui...');
  pre.textContent = '...';
  const opts = {method, headers:{}};
  if(body){opts.headers['Content-Type']='application/x-www-form-urlencoded';opts.body=body;}
  try {
    const res = await fetch(BASE+path, opts);
    let text = await res.text();
    
    // Nếu UOPZ disable exit(), WordPress sẽ render cả theme HTML đằng sau JSON
    if (text.includes('<!DOCTYPE html>')) {
        text = text.substring(0, text.indexOf('<!DOCTYPE html>'));
    }
    
    const json = JSON.parse(text);
    pre.textContent = JSON.stringify(json, null, 2);
    setStatus(n, res.ok?'ok':'err', res.ok?'OK '+res.status:'Error '+res.status);
  } catch(e) {
    pre.textContent = 'Loi: '+e.message;
    setStatus(n,'err','Network Error');
  }
}

function createProduct(){
  const b = new URLSearchParams({name:v('p_name'),description:v('p_desc'),price:v('p_price'),stock:v('p_stock')}).toString();
  call('POST','/products','r2',b,2);
}
function updateProduct(){
  const b = new URLSearchParams({name:v('u_name'),price:v('u_price')}).toString();
  call('PUT','/products/'+v('u_id'),'r4',b,4);
}
function createOrder(){
  const b = new URLSearchParams({product_id:v('o_pid'),quantity:v('o_qty')||1,customer:v('o_cust')}).toString();
  call('POST','/orders','r6',b,6);
}
</script>
</body>
</html>
<?php exit;
}

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

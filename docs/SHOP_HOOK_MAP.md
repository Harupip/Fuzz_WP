# Shop Demo Hook Map

Map nay mo ta quan he hook trong `target-app/shop-demo/shop-demo.php`.

## Function -> Hook duoc goi

- `shop_activate`
  - `shop_plugin_activated` (`do_action`)

- `shop_get_products`
  - `shop_filter_products_list` (`apply_filters`)

- `shop_get_product`
  - `shop_filter_single_product` (`apply_filters`)

- `shop_create_product`
  - `shop_before_create_product` (`apply_filters`)
  - `shop_product_created` (`do_action`)

- `shop_update_product`
  - `shop_before_update_product` (`apply_filters`)
  - `shop_product_updated` (`do_action`)

- `shop_delete_product`
  - `shop_before_delete_product` (`do_action`)
  - `shop_product_deleted` (`do_action`)

- `shop_get_orders`
  - `shop_filter_orders_list` (`apply_filters`)

- `shop_create_order`
  - `shop_calculate_order_total` (`apply_filters`)
  - `shop_order_placed` (`do_action`)

- `shop_run_hook_lab`
  - `all` (`add_filter`, `remove_filter`)
  - `shop_demo_runtime_action` (`add_action`, `do_action`, `remove_action`)
  - `shop_demo_runtime_filter` (`add_filter`, `apply_filters`, `remove_filter`)

## Hook -> Callback dang ky trong file

- `the_content`
  - `shop_append_promo_banner`

- `rest_api_init`
  - `shop_register_endpoints`

- `shop_product_created`
  - `closure@shop-demo.php:58`

- `shop_secret_admin_export`
  - `closure@shop-demo.php:304`

- `shop_process_refund`
  - `closure@shop-demo.php:308`

- `shop_send_invoice_email`
  - `closure@shop-demo.php:312`

- `template_redirect`
  - `shop_render_test_ui`

## Blindspot hooks

Nhung hook duoi day dang co callback dang ky trong file, nhung khong thay diem trigger tuong ung trong plugin demo nay:

- `shop_secret_admin_export`
- `shop_process_refund`
- `shop_send_invoice_email`

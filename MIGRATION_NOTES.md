# Odoo 16 -> Odoo 20 : PARTIAL port (work in progress)

Status: NOT fully migrated. Nothing here has been installed/tested on a real Odoo 20 server.
Verified against the real Odoo 20.0 source (addons + official odoo/upgrade_code scripts).

## Applied to ALL modules
- Version -> 20.0.1.0.0
- Official upgrade_code scripts: tree->list, deprecated properties, t-call, Owl 3 templates
- attrs= / states= (209 places) -> inline invisible/readonly/required expressions
- ir.model.access.csv -> ir.access.csv (new Odoo 20 format); dead scaffold CSVs removed
- Removed from cron XML: numbercall / doall (fields no longer exist)

## Status per module
FULLY PORTED (needs your test on staging):
- custom_inventory_picking  (rewritten as small inheritance of core 20 form; added sale_stock dependency)
- account_payment_approval  (account.payment has its own state in 20; approval flow rewritten; settings view -> <app>/<block>/<setting>)
- purchase_request          : SECURITY ONLY (ir.rule -> ir.access rows, groups -> res.groups.privilege). Python/views NOT reviewed.
- customer_credit_warning, invoice_recent_attachments_cleaner, stockinventory, website_force,
  Attendance_module_dsm, Custom_attendance : reviewed, mechanical fixes only (low risk)

NOT YET REVIEWED / KNOWN TODO (will likely fail or misbehave on Odoo 20):
- sale_account_manager_customer_credit_limit_approval: 4 <attribute name="attrs"> xpaths, sale.order.state must become selection_add
  ('done' state no longer exists, use `locked`), sale form xpaths, depends must add customer_credit_control_trial + customer_credit_warning,
  /web#id= URL -> /odoo/action-.../<id>, debug prints
- customer_credit_control_trial: settings view anchor (div[@name=catalog_setting_container] -> block), is_ceo field, debug prints
- POS modules (odoo.define legacy JS => must be rewritten): pos_warehouse_delivery, pos_credit_limit, bi_pos_restrict_zero_qty, bi_pos_customer_ref
  (bi_pos_customer_ref/views/views.xml is also a full copy of the sale order form -> must be replaced by inheritance)
- purchase_request: name_get/_name_search, groups_id, qty_done, Python+views review
- auto_database_backup, hr_biometric_attendance (settings views use data-key -> <app>), all_in_one_whatsapp_integration,
  whatsapp_mail_messaging (consider Odoo 20 native WhatsApp), pos_dashboard, warehouse_dashboard, pos_product_free_qty,
  custom_remove_powered_by_odoo (attrs + OWL)

## Left out on purpose
- customer_credit_limit/: a git repo containing exact duplicate copies of 4 modules above (+ .git/.idea)
- sale_stock_renting: Odoo Enterprise's own module, already shipped with Odoo 20 Enterprise
- DB: custom fields/tables need pre/post-migrate scripts; ir.rule xml-ids changed (purchase_request_*_rule -> access_*)

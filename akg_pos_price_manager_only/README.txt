akg_pos_price_manager_only (Odoo 20)
POS > Settings > Pricing > Price Control ON  =>  only the POS manager can change prices.
Manager = employee listed under "Manager" (POS settings, Log in with Employees).
Cashier / Supervised / Restrictive employees: Price button disabled, even if their user is a POS manager.

Install:  ./odoo-bin -c <conf> -d <db> -i akg_pos_price_manager_only --stop-after-init
Update :  ./odoo-bin -c <conf> -d <db> -u akg_pos_price_manager_only --stop-after-init
Then hard-refresh the POS (Ctrl+Shift+R) or close and reopen the POS session screen.

Fix (1.1.0): POS > Quotation/Order > settle a sale order with lot/serial (batch) tracked products
used to crash with "Cannot read properties of undefined (reading 'tracking')" in updateSOLines.
See static/src/app/settle_so_tracked_fix.js. Requires module pos_sale (already installed if the
Quotation/Order button exists in your POS).

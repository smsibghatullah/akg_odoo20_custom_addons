/** @odoo-module */

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PosStore.prototype, {
    async pay() {
        if (this.config && this.config.restrict_zero_qty) {
            const order = this.getOrder ? this.getOrder() : (this.env?.services?.pos?.getOrder ? this.env.services.pos.getOrder() : null);
            if (order) {
                const lines = order.get_orderlines ? order.get_orderlines() : (order.lines || []);
                const prodUsedQty = {};
                let restrict = false;

                for (const line of lines) {
                    const prd = line.get_product ? line.get_product() : (line.product_id || line.product);
                    const qty = line.get_quantity ? line.get_quantity() : (line.qty || 0);

                    if (prd && (prd.type === 'consu' || prd.type === 'product')) {
                        const availableQty = prd.qty_available || 0;
                        if (prd.id in prodUsedQty) {
                            prodUsedQty[prd.id][1] += qty;
                        } else {
                            prodUsedQty[prd.id] = [availableQty, qty];
                        }

                        if (availableQty <= 0) {
                            restrict = true;
                            const warning = `${prd.display_name || prd.name} is out of stock.`;
                            this.dialog.add(AlertDialog, {
                                title: _t("Zero Quantity Not Allowed"),
                                body: _t(warning),
                            });
                            return;
                        }
                    }
                }

                if (!restrict) {
                    for (const [id, [qtyAvailable, qtyRequested]] of Object.entries(prodUsedQty)) {
                        if (qtyAvailable - qtyRequested < 0) {
                            const product = this.models && this.models['product.product'] ? (this.models['product.product'].get(parseInt(id)) || this.models['product.product'].getBy('id', parseInt(id))) : null;
                            const productName = product ? (product.display_name || product.name) : _t("Product");
                            const warning = `${productName} is out of stock.`;
                            this.dialog.add(AlertDialog, {
                                title: _t("Deny Order"),
                                body: _t(warning),
                            });
                            return;
                        }
                    }
                }
            }
        }
        return super.pay(...arguments);
    },
});
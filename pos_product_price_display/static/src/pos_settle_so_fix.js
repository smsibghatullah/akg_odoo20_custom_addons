import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    /**
     * Settling a sale order crashed with "Cannot read properties of undefined (reading 'tracking')"
     * when a line's product is not loaded in this POS (product not "Available in POS", archived, ...):
     * pos_sale_stock reads newLine.getProduct().tracking. The line is skipped with a clear message
     * naming the product, the other lines are settled normally.
     */
    async updateSOLines(line, convertedLine, newLine, newLineValues, state) {
        const product = newLine?.getProduct?.();
        if (!product) {
            newLine?.delete?.();
            this.notification.add(
                _t(
                    "Product '%s' is not available in this Point of Sale, its line was skipped. " +
                        "Enable 'Available in POS' on the product and settle again.",
                    line?.name || line?.product_id?.display_name || "?"
                ),
                { type: "warning", sticky: true }
            );
            return;
        }
        return super.updateSOLines(...arguments);
    },

    splitSOLine(line, convertedLine, newLine, newLineValues, state) {
        if (!line?.product_id) {
            return [];
        }
        return super.splitSOLine(...arguments);
    },
});

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

/**
 * Fix: settling a quotation / sale order in the POS crashes with
 *   TypeError: Cannot read properties of undefined (reading 'tracking')   (updateSOLines)
 * when the order contains a lot/serial (batch) tracked product.
 *
 * Cause: for a tracked product the line-adding code (a lot/serial check, shown as the toast
 * "... was not added: a lot/serial number is required") returns `undefined` instead of the
 * new order line. settleSO() then passes that `undefined` to updateSOLines() and it crashes,
 * so the whole sale order is never loaded.
 *
 * Fix: while a sale order is being settled, if the normal add-line path did not return a line,
 * the line is created directly (same way Odoo's own splitSOLine does). The lot/serial number
 * can then be entered on the line (lot icon) or at payment, as usual. updateSOLines also
 * ignores a missing line instead of crashing.
 */
patch(PosStore.prototype, {
    async settleSO(sale_order, orderFiscalPos) {
        this._akgSettlingSO = true;
        try {
            return await super.settleSO(...arguments);
        } finally {
            this._akgSettlingSO = false;
        }
    },

    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        const line = await super.addLineToCurrentOrder(...arguments);
        if (line || !this._akgSettlingSO || !vals?.sale_order_line_id) {
            return line;
        }
        // sale order line that was refused (lot/serial required): add it without the check
        const order = this.getOrder();
        if (!order || !vals.product_id) {
            return line;
        }
        const newLine = this.models["pos.order.line"].create({ ...vals, order_id: order });
        this.selectOrderLine?.(order, newLine);
        return newLine;
    },

    async updateSOLines(line, convertedLine, newLine) {
        if (!newLine || !line?.product_id) {
            return;
        }
        return super.updateSOLines(...arguments);
    },
});

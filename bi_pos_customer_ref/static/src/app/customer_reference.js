/** Odoo 20 PoS: "Customer Reference" button + persisted order field.
 *  Replaces the legacy odoo.define / Registries based code of Odoo 16. */
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { TextInputPopup } from "@point_of_sale/app/components/popups/text_input_popup/text_input_popup";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";

// `customer_reference` is a field of pos.order (loaded & serialized by the generic PoS data layer);
// we only need to give it a default value on new orders.
patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(...arguments);
        this.customer_reference = vals.customer_reference || "";
    },
});

patch(ControlButtons.prototype, {
    async clickCustomerReference() {
        const order = this.pos.getOrder();
        if (!order) {
            return;
        }
        const payload = await makeAwaitable(this.dialog, TextInputPopup, {
            title: _t("Enter Customer Reference"),
            placeholder: _t("Customer reference"),
            startingValue: order.customer_reference || "",
        });
        if (typeof payload === "string") {
            order.customer_reference = payload.trim();
        }
    },
});

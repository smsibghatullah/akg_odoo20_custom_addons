import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PosAccessRightPlugin } from "@point_of_sale/app/plugins/access_right_plugin";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(PosAccessRightPlugin.prototype, {
    /** true only for a POS manager (see models/hr_employee.py for the rule) */
    get akgIsPriceManager() {
        const cashier = this.loggedCashier;
        if (!cashier) {
            return false;
        }
        if (cashier._price_manager !== undefined) {
            return !!cashier._price_manager;
        }
        return cashier._role === "manager";
    },

    get disablePriceButton() {
        return (
            super.disablePriceButton ||
            (!!this.config.restrict_price_control && !this.akgIsPriceManager)
        );
    },
});

patch(ProductScreen.prototype, {
    onNumpadClick(buttonValue) {
        if (this.pos.accessRight.disablePriceButton) {
            if (buttonValue === "price") {
                this.dialog.add(AlertDialog, {
                    title: _t("Price change not allowed"),
                    body: _t("Only the POS manager can change the price."),
                });
                return;
            }
            if (this.pos.numpadMode === "price") {
                // a cashier must never type into the price field (e.g. after switching cashier)
                this.pos.numpadMode = "quantity";
            }
        }
        return super.onNumpadClick(...arguments);
    },
});

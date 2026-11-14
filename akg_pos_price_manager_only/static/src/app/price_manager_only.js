import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PosAccessRightPlugin } from "@point_of_sale/app/plugins/access_right_plugin";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(PosAccessRightPlugin.prototype, {
    /** true only for a POS manager (rule: models/hr_employee.py) */
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

    /**
     * Price Control ON  -> locked for everybody who is not a price manager.
     * The decision is made HERE only: other patches of `disablePriceButton` (Odoo or custom POS modules)
     * must not be able to lock a manager out, nor to unlock a cashier.
     */
    get akgPriceLocked() {
        return !!this.config.restrict_price_control && !this.akgIsPriceManager;
    },

    get disablePriceButton() {
        if (this.config.restrict_price_control) {
            return this.akgPriceLocked;
        }
        return super.disablePriceButton;
    },
});

patch(ProductScreen.prototype, {
    getNumpadButtons() {
        const buttons = super.getNumpadButtons(...arguments);
        if (!this.pos.config.restrict_price_control) {
            return buttons;
        }
        const locked = this.pos.accessRight.akgPriceLocked;
        const isCombo = !!this.currentOrder?.getSelectedOrderline()?.isPartOfCombo();
        return buttons.map((button) =>
            button.value === "price" ? { ...button, disabled: locked || isCombo } : button
        );
    },

    onNumpadClick(buttonValue) {
        if (this.pos.config.restrict_price_control) {
            const locked = this.pos.accessRight.akgPriceLocked;
            if (buttonValue === "price") {
                if (locked) {
                    const cashier = this.pos.accessRight.loggedCashier;
                    const info = `${cashier?.name || "?"} | role: ${cashier?._role} | price manager: ${cashier?._price_manager}`;
                    // eslint-disable-next-line no-console
                    console.warn("[akg_pos_price_manager_only] price blocked for:", info, cashier);
                    this.dialog.add(AlertDialog, {
                        title: _t("Price change not allowed"),
                        body: _t("Only the POS manager can change the price.") + "\n\n(" + info + ")",
                    });
                    return;
                }
                // price manager: switch to price mode here (same as the standard code)
                this.numberBuffer.capture();
                this.numberBuffer.reset();
                this.pos.numpadMode = "price";
                return;
            }
            if (locked && this.pos.numpadMode === "price") {
                // a cashier must never type into the price field (e.g. after switching cashier)
                this.pos.numpadMode = "quantity";
            }
        }
        return super.onNumpadClick(...arguments);
    },
});

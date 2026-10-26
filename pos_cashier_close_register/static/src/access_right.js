import { PosAccessRightPlugin } from "@point_of_sale/app/plugins/access_right_plugin";
import { patch } from "@web/core/utils/patch";

// pos_hr allows closing the register for "manager" only -> allow "cashier" too.
patch(PosAccessRightPlugin.prototype, {
    get canCloseSession() {
        return this.hasEmployeeRole(["cashier", "manager"]);
    },
});

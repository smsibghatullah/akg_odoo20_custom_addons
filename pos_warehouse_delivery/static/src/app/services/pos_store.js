import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    /**
     * Warehouse pre-selected on every new orderline:
     * POS "Default Warehouse" -> POS warehouse -> first available warehouse.
     */
    getDefaultWarehouse() {
        const warehouses = this.models["stock.warehouse"];
        // config fields can be a loaded record or a bare id
        const resolve = (wh) => {
            if (!wh) {
                return null;
            }
            return typeof wh === "object" ? wh : warehouses.get(wh) || null;
        };
        const config = this.config;
        return (
            resolve(config.default_warehouse_id) ||
            resolve(config.picking_type_id?.warehouse_id) ||
            warehouses.getAll()[0]
        );
    },

    async addLineToOrder(vals, order, opts = {}, configure = true) {
        if (this.config.enable_warehouse_delivery && !vals.warehouse_id) {
            const warehouse = this.getDefaultWarehouse();
            if (warehouse) {
                vals.warehouse_id = warehouse.id;
            }
        }
        return super.addLineToOrder(vals, order, opts, configure);
    },
});

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

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

    /** True when a lot / serial number must be entered for this product on this POS. */
    isLotRequiredFor(product) {
        return Boolean(
            product &&
                ["lot", "serial"].includes(product.tracking) &&
                (this.pickingType?.use_create_lots || this.pickingType?.use_existing_lots)
        );
    },

    /** Warehouse whose lots are offered: pending choice > selected line > default. */
    getLotWarehouseId() {
        if (this._lotWarehouseId) {
            return this._lotWarehouseId;
        }
        const order = this.getOrder?.();
        const line = order?.getSelectedOrderline?.();
        return line?.warehouse_id?.id || this.getDefaultWarehouse()?.id || false;
    },

    /**
     * Same popup as core, but get_existing_lots receives the warehouse so only
     * the lots with stock in that warehouse are offered.
     */
    async editLots(product, packLotLinesToEdit) {
        const warehouseId = this.config.enable_warehouse_delivery && this.getLotWarehouseId();
        if (!warehouseId) {
            return super.editLots(...arguments);
        }
        const data = this.data;
        const hadOwnCall = Object.prototype.hasOwnProperty.call(data, "call");
        const originalCall = data.call;
        data.call = function (model, method, args, ...rest) {
            if (model === "pos.order.line" && method === "get_existing_lots") {
                args = [...args, warehouseId];
            }
            return originalCall.call(this, model, method, args, ...rest);
        };
        try {
            return await super.editLots(...arguments);
        } finally {
            if (hadOwnCall) {
                data.call = originalCall;
            } else {
                delete data.call;
            }
        }
    },

    /**
     * Warehouse of a tracked line was changed: ask for lots of the NEW warehouse,
     * and only if one is chosen replace the old lots and change the warehouse.
     * Returns false when the user cancelled (the caller keeps the old warehouse).
     */
    async repickLotsForWarehouse(line, warehouseId) {
        const product = line.product_id;
        const previous = this._lotWarehouseId;
        this._lotWarehouseId = warehouseId;
        let payload;
        try {
            payload = await this.editLots(product, []);
        } finally {
            this._lotWarehouseId = previous;
        }
        if (!payload) {
            return false;
        }
        for (const lot of [...(line.pack_lot_ids || [])]) {
            if (typeof lot.delete === "function") {
                lot.delete();
            } else {
                this.models["pos.pack.operation.lot"].delete?.(lot);
            }
        }
        line.update({ warehouse_id: warehouseId });
        line.editPackLotLines(payload);
        return true;
    },

    _notifyLotRequired(product) {
        const notification = this.notification || this.env?.services?.notification;
        notification?.add?.(
            _t("%s was not added: a lot/serial number is required.", product.display_name),
            { type: "warning" }
        );
    },

    async addLineToOrder(vals, order, opts = {}, configure = true) {
        if (!this.config.enable_warehouse_delivery) {
            return super.addLineToOrder(vals, order, opts, configure);
        }
        if (!vals.warehouse_id) {
            const warehouse = this.getDefaultWarehouse();
            if (warehouse) {
                vals.warehouse_id = warehouse.id;
            }
        }

        // lots offered in the popup must come from this line's warehouse
        const targetOrder = order || this.getOrder();
        const linesBefore = [...(targetOrder?.lines || [])];
        const previous = this._lotWarehouseId;
        const wh = vals.warehouse_id;
        this._lotWarehouseId = (typeof wh === "object" ? wh?.id : wh) || false;
        let result;
        try {
            result = await super.addLineToOrder(vals, order, opts, configure);
        } finally {
            this._lotWarehouseId = previous;
        }

        // a tracked product can not stay in the order without a lot / serial number
        const product = vals.product_id;
        const isRefund = vals.refunded_orderline_id || (vals.qty ?? 1) < 0;
        if (targetOrder && !isRefund && this.isLotRequiredFor(product)) {
            const added = (targetOrder.lines || []).filter((l) => !linesBefore.includes(l));
            for (const line of added) {
                if (!line.hasValidProductLot?.()) {
                    if (typeof targetOrder.removeOrderline === "function") {
                        targetOrder.removeOrderline(line);
                    } else if (typeof line.delete === "function") {
                        line.delete();
                    }
                    this._notifyLotRequired(product);
                }
            }
        }
        return result;
    },
});

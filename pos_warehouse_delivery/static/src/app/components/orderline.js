import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;
const INPUT_FORMAT = "yyyy-MM-dd'T'HH:mm";
const LABEL_FORMAT = "dd/MM/yyyy HH:mm";

patch(Orderline.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    },

    /** Show the warehouse block only on lines of the order being edited */
    get showWarehouseInfo() {
        const order = this.line.order_id;
        return Boolean(
            this.props.mode === "display" &&
                !this.props.toRefund &&
                this.pos.config.enable_warehouse_delivery &&
                order &&
                order.state === "draft" &&
                !order.isRefund &&
                this.line.qty >= 0
        );
    },

    get warehouseOptions() {
        return this.pos.models["stock.warehouse"].getAll();
    },

    /** Warehouse pre-selected on the POS (config Default Warehouse) */
    get defaultWarehouse() {
        return this.pos.getDefaultWarehouse();
    },

    /** Line warehouse, falling back to the POS default for lines without one */
    get selectedWarehouse() {
        return this.line.warehouse_id || this.defaultWarehouse || false;
    },

    get selectedWarehouseId() {
        return this.selectedWarehouse?.id || false;
    },

    get warehouseName() {
        return this.selectedWarehouse?.name || "";
    },

    get allowShipLater() {
        return Boolean(this.pos.config.allow_ship_later);
    },

    get isShipLater() {
        return Boolean(this.line.ship_later);
    },

    get shipLaterDateValue() {
        const date = this.line.ship_later_date;
        return date && date.isValid ? date.toFormat(INPUT_FORMAT) : "";
    },

    get shipLaterDateLabel() {
        const date = this.line.ship_later_date;
        return date && date.isValid ? date.toFormat(LABEL_FORMAT) : "";
    },

    stopEvent(ev) {
        ev.stopPropagation();
    },

    async onWarehouseChange(ev) {
        ev.stopPropagation();
        const select = ev.target;
        const id = parseInt(select.value);
        const warehouseId = isNaN(id) ? false : id;
        const oldId = this.line.warehouse_id?.id || this.selectedWarehouseId || "";
        const product = this.line.product_id;
        if (
            warehouseId &&
            warehouseId !== oldId &&
            this.pos.isLotRequiredFor(product) &&
            !this.line.refunded_orderline_id
        ) {
            // lots belong to a warehouse: the old lot is dropped and one lot of
            // the new warehouse must be chosen (cancel keeps the old warehouse)
            const done = await this.pos.repickLotsForWarehouse(this.line, warehouseId);
            if (!done) {
                select.value = String(oldId);
            }
            return;
        }
        this.line.update({ warehouse_id: warehouseId });
    },

    onShipLaterToggle(ev) {
        ev.stopPropagation();
        const checked = ev.target.checked;
        const vals = { ship_later: checked };
        if (checked && !this.line.ship_later_date) {
            vals.ship_later_date = DateTime.now();
        }
        this.line.update(vals);
    },

    onShipLaterDateChange(ev) {
        ev.stopPropagation();
        const date = DateTime.fromFormat(ev.target.value || "", INPUT_FORMAT);
        if (date.isValid) {
            this.line.update({ ship_later_date: date });
        }
    },
});

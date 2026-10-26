import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";
import { proxy } from "@odoo/owl";

const { DateTime } = luxon;
const INPUT_FORMAT = "yyyy-MM-dd'T'HH:mm";

/**
 * Refund panel of the Orders screen (right side, "Select the product(s) to refund"):
 * every refundable line gets a Warehouse dropdown + Ship Later checkbox.
 * The choice is copied to the refund order line when "Refund" is pressed.
 */
patch(TicketScreen.prototype, {
    setup() {
        super.setup(...arguments);
        // line.uuid -> { warehouse_id, ship_later, ship_later_date }
        this.refundWh = proxy({});
    },

    get whEnabled() {
        return Boolean(this.pos.config.enable_warehouse_delivery);
    },

    get whAllowShipLater() {
        return Boolean(this.pos.config.allow_ship_later);
    },

    get whOptions() {
        return this.pos.models["stock.warehouse"].getAll();
    },

    /** Controls are shown for synced, non-refund orders, on lines that can still be refunded */
    whShowFor(line) {
        const order = line.order_id;
        return Boolean(
            this.whEnabled &&
                this.isOrderSynced &&
                order &&
                !order.isRefund &&
                !order.is_refund &&
                !line.refunded_orderline_id &&
                line.qty > 0
        );
    },

    /** Chosen values of a line (read only: nothing is written while rendering) */
    whGet(line) {
        if (this.refundWh[line.uuid]) {
            return this.refundWh[line.uuid];
        }
        const wh = line.warehouse_id || this.pos.getDefaultWarehouse();
        return {
            warehouse_id: wh ? wh.id : false,
            ship_later: false,
            ship_later_date: false,
        };
    },

    whSet(line, vals) {
        this.refundWh[line.uuid] = { ...this.whGet(line), ...vals };
    },

    whName(line) {
        const id = this.whGet(line).warehouse_id;
        const wh = id && this.pos.models["stock.warehouse"].get(id);
        return wh ? wh.name : "";
    },

    whDateValue(line) {
        const date = this.whGet(line).ship_later_date;
        return date && date.isValid ? date.toFormat(INPUT_FORMAT) : "";
    },

    whStop(ev) {
        ev.stopPropagation();
    },

    onWhChange(line, ev) {
        ev.stopPropagation();
        const id = parseInt(ev.target.value);
        this.whSet(line, { warehouse_id: isNaN(id) ? false : id });
    },

    onWhShipLaterToggle(line, ev) {
        ev.stopPropagation();
        const checked = ev.target.checked;
        const vals = { ship_later: checked };
        if (checked && !this.whGet(line).ship_later_date) {
            vals.ship_later_date = DateTime.now();
        }
        this.whSet(line, vals);
    },

    onWhShipLaterDateChange(line, ev) {
        ev.stopPropagation();
        const date = DateTime.fromFormat(ev.target.value || "", INPUT_FORMAT);
        if (date.isValid) {
            this.whSet(line, { ship_later_date: date });
        }
    },

    /** Copy the chosen warehouse / ship later to the refund order line */
    getRefundLinesDetails(refundDetail, destinationOrder) {
        const vals = super.getRefundLinesDetails(...arguments);
        if (this.whEnabled) {
            const chosen = this.whGet(refundDetail.line);
            if (chosen.warehouse_id) {
                vals.warehouse_id = chosen.warehouse_id;
            }
            vals.ship_later = Boolean(chosen.ship_later);
            if (chosen.ship_later && chosen.ship_later_date) {
                vals.ship_later_date = chosen.ship_later_date;
            }
        }
        return vals;
    },
});

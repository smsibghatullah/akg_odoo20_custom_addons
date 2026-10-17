/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, proxy } from "@odoo/owl";

const COLOR_PALETTE = [
    "#1f8ecd", "#f4a83d", "#e91e8c", "#f2c94c",
    "#8e44ad", "#16a085", "#e74c3c", "#27ae60",
    "#3498db", "#d35400",
];

export class PosDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = proxy({
            posList: [],
            loading: true,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        const data = await this.orm.call(
            "pos.dashboard",
            "get_dashboard_data",
            []
        );
        data.forEach((pos, idx) => {
            pos.color = COLOR_PALETTE[idx % COLOR_PALETTE.length];
        });
        this.state.posList = data;
        this.state.loading = false;
    }

    async refresh() {
        await this.loadData();
    }

    _openList(name, resModel, domain) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: resModel,
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: domain,
            target: "current",
        });
    }

    _nowStr() {
        const d = new Date();
        const pad = (n) => String(n).padStart(2, "0");
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
    }

    // Delivery Orders: matched via pos_order_id -> session_id -> config_id
    // (unchanged). Internal Transfers: matched via the POS's default
    // warehouse (picking_type_id.warehouse_id).
    _pickingDomain(pos, code, statType) {
        const domain = [["picking_type_id.code", "=", code]];

        if (code === "internal") {
            domain.push(["picking_type_id.warehouse_id", "in", pos.warehouse_ids]);
        } else {
            domain.push(["pos_order_id.session_id.config_id", "in", pos.config_ids]);
        }

        if (statType === "waiting") {
            domain.push(["state", "in", ["confirmed", "waiting"]]);
        } else if (statType === "late") {
            domain.push(["state", "not in", ["done", "cancel"]]);
            domain.push(["scheduled_date", "<", this._nowStr()]);
        } else if (statType === "backorders") {
            domain.push(["state", "not in", ["done", "cancel"]]);
            domain.push(["backorder_id", "!=", false]);
        } else {
            domain.push(["state", "not in", ["done", "cancel"]]);
        }
        return domain;
    }

    openPicking(pos, code, label, statType, ev) {
        if (ev) ev.stopPropagation();
        const domain = this._pickingDomain(pos, code, statType);
        this._openList(`${label} - ${pos.pos_name}`, "stock.picking", domain);
    }
}

PosDashboard.template = "pos_dashboard.PosDashboard";

registry.category("actions").add("pos_dashboard_tag", PosDashboard);

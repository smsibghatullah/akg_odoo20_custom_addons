/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, proxy, usePlugin } from "@odoo/owl";
import { ActionManagerPlugin } from "@web/webclient/actions/action_plugin";

const COLOR_PALETTE = [
    "#1f8ecd", "#f4a83d", "#e91e8c", "#f2c94c",
    "#8e44ad", "#16a085", "#e74c3c", "#27ae60",
    "#3498db", "#d35400",
];

export class WarehouseDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = usePlugin(ActionManagerPlugin);

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
            "warehouse.dashboard",
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

    _todayStr() {
        const d = new Date();
        const pad = (n) => String(n).padStart(2, "0");
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} 00:00:00`;
    }

    _pickingDomain(pos, code, statType) {
        const domain = [
            ["picking_type_id.warehouse_id", "=", pos.warehouse_id],
            ["picking_type_id.code", "=", code],
        ];
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
        this._openList(`${label} - ${pos.warehouse_name}`, "stock.picking", domain);
    }

    openPos(pos, statType, ev) {
        if (ev) ev.stopPropagation();
        const domain = [
            ["session_id.config_id", "=", pos.pos_id],
            ["state", "=", "paid"],
        ];
        if (statType === "today") {
            domain.push(["date_order", ">=", this._todayStr()]);
        }
        this._openList(`PoS Orders - ${pos.pos_name}`, "pos.order", domain);
    }
}

WarehouseDashboard.template = "warehouse_dashboard.WarehouseDashboard";

registry.category("actions").add("warehouse_dashboard_tag", WarehouseDashboard);

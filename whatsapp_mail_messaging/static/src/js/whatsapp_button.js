/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class WhatsappSystrayItem extends Component {
    static template = "whatsapp_mail_messaging.whatsapp_icon";

    setup() {
        this.action = useService("action");
    }

    onClickWhatsappIcon() {
        this.action.doAction({
            name: "Compose Whatsapp Message",
            res_model: "whatsapp.message.wizard",
            views: [[false, "form"]],
            type: "ir.actions.act_window",
            view_mode: "form",
            target: "new",
        });
    }
}

registry
    .category("systray")
    .add("whatsapp_mail_messaging.whatsapp_icon", { Component: WhatsappSystrayItem }, { sequence: 25 });
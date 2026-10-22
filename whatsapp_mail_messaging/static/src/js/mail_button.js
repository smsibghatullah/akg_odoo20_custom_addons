/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class MailSystrayItem extends Component {
    static template = "global_mail_message.mail_icon";
    static props = {};

    setup() {
        this.action = useService("action");
    }

    onClickMailIcon() {
        this.action.doAction({
            name: "Compose Mail",
            res_model: "mail.compose.message",
            views: [[false, "form"]],
            type: "ir.actions.act_window",
            view_mode: "form",
            target: "new",
        });
    }
}

registry
    .category("systray")
    .add("global_mail_message.mail_icon", { Component: MailSystrayItem }, { sequence: 24 });
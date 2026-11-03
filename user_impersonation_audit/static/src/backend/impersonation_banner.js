import { Component, onMounted, onWillDestroy, proxy, t, useProps } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { Dialog } from "@web/core/dialog/dialog";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { formatRemaining, postReturn } from "./impersonation_utils";

const WARNING_SECONDS = 5 * 60;

export class ImpersonationExtendDialog extends Component {
    static template = "user_impersonation_audit.ExtendDialog";
    static components = { Dialog };
    props = useProps({ close: t.function(), minLength: t.number(), onExtended: t.function() });

    setup() {
        this.state = proxy({ reason: "", busy: false });
    }

    onInput(ev) {
        this.state.reason = ev.target.value;
    }

    get tooShort() {
        return this.state.reason.trim().length < this.props.minLength;
    }

    async confirm() {
        if (this.tooShort || this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            const result = await rpc("/impersonation/extend", { reason: this.state.reason });
            this.props.onExtended(result.remaining);
            this.props.close();
        } finally {
            this.state.busy = false;
        }
    }
}

export class ImpersonationBanner extends Component {
    static template = "user_impersonation_audit.Banner";
    props = useProps({});

    setup() {
        this.info = session.impersonation;
        this.dialog = useService("dialog");
        this.state = proxy({ remaining: this.info.remaining, canExtend: this.info.can_extend });
        this.deadline = Date.now() + this.info.remaining * 1000;
        this.interval = browser.setInterval(() => this.tick(), 1000);
        onMounted(() => document.body.classList.add("o_uia_active"));
        onWillDestroy(() => {
            browser.clearInterval(this.interval);
            document.body.classList.remove("o_uia_active");
        });
    }

    get timeLeft() {
        return formatRemaining(this.state.remaining);
    }

    get isWarning() {
        return this.state.remaining < WARNING_SECONDS;
    }

    tick() {
        this.state.remaining = Math.max(0, Math.round((this.deadline - Date.now()) / 1000));
        if (this.state.remaining === 0 && !this.leaving) {
            this.leaving = true;
            this.returnToAccount();
        }
    }

    returnToAccount() {
        postReturn();
    }

    openExtend() {
        this.dialog.add(ImpersonationExtendDialog, {
            minLength: this.info.min_reason_length,
            onExtended: (remaining) => {
                this.deadline = Date.now() + remaining * 1000;
                this.state.canExtend = false;
                this.tick();
            },
        });
    }
}


if (session.impersonation) {
    registry.category("main_components").add("user_impersonation_audit.Banner", {
        Component: ImpersonationBanner,
    });
}

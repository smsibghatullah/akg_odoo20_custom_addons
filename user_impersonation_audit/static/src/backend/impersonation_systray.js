import { Component, proxy, useProps } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { session } from "@web/session";

const WIZARD = "user.impersonation.wizard";

export class ImpersonationPicker extends Component {
    static template = "user_impersonation_audit.Picker";
    static components = { Dropdown };
    props = useProps({});

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dropdown = useDropdownState();
        this.state = proxy({ query: "", groupId: 0, users: [], groups: [], loaded: false });
        this.debouncedSearch = useDebounced(() => this.search(), 250);
    }

    async onBeforeOpen() {
        if (!this.state.groups.length) {
            this.state.groups = await this.orm.call(WIZARD, "uia_picker_groups", []);
        }
        await this.search();
    }

    async search() {
        this.state.users = await this.orm.call(WIZARD, "uia_search_targets", [
            this.state.query,
            this.state.groupId || false,
        ]);
        this.state.loaded = true;
    }

    onInput(ev) {
        this.state.query = ev.target.value;
        this.debouncedSearch();
    }

    onGroupChange(ev) {
        this.state.groupId = parseInt(ev.target.value) || 0;
        this.search();
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && this.state.users.length) {
            this.openWizard(this.state.users[0]);
        }
    }

    async toggleFavorite(user) {
        user.favorite = await this.orm.call(WIZARD, "uia_toggle_favorite", [user.id]);
    }

    openWizard(user) {
        this.dropdown.close();
        const here = browser.location.pathname + browser.location.search;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Log in as %s", user.name),
            res_model: WIZARD,
            views: [[false, "form"]],
            target: "new",
            context: {
                default_target_id: user.id,
                default_landing_url: here,
                default_return_url: here,
            },
        });
    }
}

if (session.impersonation_can_start) {
    registry
        .category("systray")
        .add("user_impersonation_audit.Picker", { Component: ImpersonationPicker }, { sequence: 5 });
}

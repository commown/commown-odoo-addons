/** @odoo-module */

import {ControlPanel} from "@web/search/control_panel/control_panel";
import {patch} from "@web/core/utils/patch";
import {session} from "@web/session";

patch(ControlPanel.prototype, "customer_team_manager.ControlPanel", {
    /**
     * If the current user is a customer (ie. not an internal user),
     * filter out the Favorites menu.
     */
    get searchMenus() {
        var searchMenus = this._super();
        if (session.is_customer) {
            searchMenus.pop("favorite");
        }
        return searchMenus;
    },
});

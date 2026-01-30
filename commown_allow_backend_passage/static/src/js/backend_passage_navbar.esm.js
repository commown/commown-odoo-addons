/** @odoo-module */

import {NavBar} from "@web/webclient/navbar/navbar";
import {patch} from "@web/core/utils/patch";
import {session} from "@web/session";

patch(NavBar.prototype, "commown_allow_backend_passage_navbar", {
    /**
     * @override
     * Filters all mail-related NavBar menu items from the Systray Items,
     * if the current user is not an internal user (has the `group_user` group)
     *
     * We do this since these menus try to access records only accessible to internal users,
     * which can provoke an access error to customer admins (portal users).
     */
    get systrayItems() {
        var navbar_items = this._super();
        if (session.is_customer) {
            navbar_items = navbar_items.filter((item) => !item.key.includes("mail"));
        }
        return navbar_items;
    },
});

/** @odoo-module */

import {browser} from "@web/core/browser/browser";
import {registry} from "@web/core/registry";

const userMenuItemsRegistry = registry.category("user_menuitems");

function portalAccount(env) {
    const url = `${browser.location.origin}/my/home`;
    return {
        type: "item",
        id: "menu-personal-area",
        description: env._t("My account"),
        href: url,
        callback: () => {
            browser.open(url, "_self");
        },
        sequence: 35,
        // This is 5 less than the separator menu item's sequence.
    };
}

userMenuItemsRegistry.add("portal_account", portalAccount);

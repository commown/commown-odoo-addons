/** @odoo-module */

import {DynamicGroupList} from "@web/views/relational_model";
import {patch} from "@web/core/utils/patch";

patch(DynamicGroupList, "DynamicGroupList web_increase_default_load_limit", {
    DEFAULT_LOAD_LIMIT: 20,
});

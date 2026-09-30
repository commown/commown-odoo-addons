/**  @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Thread",
    fields: {
        /**
         * @overload
         * Set to false to disable Audio/Video call buttons and Call options menu
         * in thread view.
         */
        hasCallFeature: false,
    },
});

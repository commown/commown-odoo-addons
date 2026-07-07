/** @odoo-module **/

import publicWidget from "web.public.widget";

publicWidget.registry.SponsoringCodeCopy = publicWidget.Widget.extend({
    selector: ".o_portal_sponsoring",
    /**
     * @override
     */
    start: function () {
        // eslint-disable-next-line no-undef, no-new
        new ClipboardJS(this.$el.find(".copy-to-clipboard")[0]);
    },
});

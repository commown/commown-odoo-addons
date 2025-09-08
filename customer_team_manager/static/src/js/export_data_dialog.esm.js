/** @odoo-module */

import {onMounted, useRef} from "@odoo/owl";
import {ExportDataDialog} from "@web/views/view_dialogs/export_data_dialog";
import {patch} from "@web/core/utils/patch";
import {session} from "@web/session";

patch(ExportDataDialog.prototype, "customer_admin", {
    /**
        Override the export widget to simplify it for customer admins
    */
    setup() {
        this._super(...arguments);
        this.export_left_panel = useRef("left_panel");
        this.export_right_panel = useRef("right_panel");
        this.import_compat_input = useRef("import_compat");
        onMounted(() => {
            if (session.is_customer) {
                // Make css customization easy to accomodate the UI:
                this.export_left_panel.el.classList.add("js-is-customer");
                this.export_right_panel.el.classList.add("js-is-customer");

                // Remove width and height related classes of the left_panel,
                // to place the export file format input better.
                this.export_left_panel.el.classList.remove("col-md-6");
                this.export_left_panel.el.classList.remove("h-100");
            }
            // Automatically check the "import-compatible" checkbox when the
            // UI is loaded, as it's unchecked by default.
            this.import_compat_input.el.firstChild.firstElementChild.click();
        });
    },
});

/** @odoo-module */

import {KanbanController} from "@web/views/kanban/kanban_controller";
import {kanbanView} from "@web/views/kanban/kanban_view";
import {registry} from "@web/core/registry";

export class KanbanImportController extends KanbanController {
    /**
     * As the import action gets moved from the Favorites menu to an action menu from Odoo 17 onwards,
     * this feature should be removable when we migrate to a newer Odoo version.
     */
    importRecords() {
        const {context, resModel} = this.env.searchModel;
        this.actionService.doAction({
            type: "ir.actions.client",
            tag: "import",
            params: {model: resModel, context},
        });
    }
}

export const KanbanImportButton = {
    ...kanbanView,
    Controller: KanbanImportController,
    buttonTemplate: "customer_team_manager.Buttons.KanbanImport",
};

registry.category("views").add("kanban_import_button", KanbanImportButton);

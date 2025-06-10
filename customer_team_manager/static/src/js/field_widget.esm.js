/** @odoo-module */

import {Many2ManyTagsField} from "@web/views/fields/many2many_tags/many2many_tags_field";
import {registry} from "@web/core/registry";

export class CustomerRoleTagsField extends Many2ManyTagsField {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.short_tag = false;
        this.props.canCreate = false;
    }

    /**
     * @override
     */
    getTagProps(record) {
        var tag_props = super.getTagProps(record);

        tag_props.display_name = record.data.display_name;
        tag_props.description = record.data.description;
        tag_props.color = record.data.color;
        tag_props.icon_name = record.data.icon_name;
        tag_props.readonly = record.data.readonly;
        tag_props.short = this.short_tag;

        return tag_props;
    }
}

CustomerRoleTagsField.template = "customer_team_manager.CustomerRoleTagsField";
CustomerRoleTagsField.fieldsToFetch = {
    display_name: {type: "char"},
    description: {type: "char"},
    color: {type: "char"},
    icon_name: {type: "char"},
    readonly: {type: "boolean"},
};

export class KanbanCustomerRoleTagsField extends CustomerRoleTagsField {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.short_tag = true;
        this.props.readonly = true;
    }

    /**
     * @override
     */
    getTagProps(record) {
        var tag_props = super.getTagProps(record);

        delete tag_props.onDelete;

        return tag_props;
    }
}

registry.category("fields").add("customer_role_tag_widget", CustomerRoleTagsField);
registry
    .category("fields")
    .add("customer_role_tag_kanban_widget", KanbanCustomerRoleTagsField);

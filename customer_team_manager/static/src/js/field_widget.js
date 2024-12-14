odoo.define("customer_role_tag_widget", function (require) {
  "use strict";

  var ajax = require('web.ajax');
  var core = require('web.core');
  var AbstractField = require('web.AbstractField');
  var FieldMany2ManyTags = require('web.relational_fields').FieldMany2ManyTags;
  var fieldRegistry = require('web.field_registry');

  ajax.loadXML('/customer_team_manager/static/src/xml/field_widget_template.xml', core.qweb);

  var FieldCustomerRoleTags = FieldMany2ManyTags.extend({
    tag_template: "FieldCustomerRoleTags",

    short_tag: false,  // If true, do not display the name of the entity

    fieldsToFetch: {
        display_name: {type: 'char'},
        description: {type: 'char'},
        color: {type: 'char'},
        icon_name: {type: 'char'},
        readonly: {type: 'boolean'},
    },

    _getRenderTagsContext: function () {
      let result = this._super.apply(this, arguments);
      result.short = this.short_tag;
      result.nodelete = this.mode === "readonly";
      return result;
    },

    /**
     * Prevent removal of readonly tags
     *
     * @override
     */
    _removeTag: function (id) {
      var record = _.findWhere(this.value.data, {res_id: id});
      if (!record.data.readonly) {
        return this._super.apply(this, arguments);
      }
    },

  });


  var FieldKanbanCustomerRoleTags = FieldCustomerRoleTags.extend({
    // Disable events to make sure the click on a card only opens it
    events: AbstractField.prototype.events,

    // Alaways display a short version of the tag (without the name)
    short_tag: true,
  });


  fieldRegistry.add('customer_role_tag_widget', FieldCustomerRoleTags);
  fieldRegistry.add('customer_role_tag_kanban_widget', FieldKanbanCustomerRoleTags);

});

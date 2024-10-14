odoo.define("employee_role_tag_widget", function (require) {
  "use strict";

  var ajax = require('web.ajax');
  var core = require('web.core');
  var FieldMany2ManyTags = require('web.relational_fields').FieldMany2ManyTags;
  var fieldRegistry = require('web.field_registry');

  ajax.loadXML('/customer_team_manager/static/src/xml/field_widget_template.xml', core.qweb);

  var FieldEmployeeRoleTags = FieldMany2ManyTags.extend({
    tag_template: "FieldEmployeeRoleTags",
    fieldsToFetch: {
        display_name: {type: 'char'},
        description: {type: 'char'},
        color: {type: 'char'},
        icon_name: {type: 'char'},
        nodelete: {type: 'boolean'},
    },
    _getRenderTagsContext: function () {
      let result = this._super.apply(this, arguments);
      result.short = !!this.nodeOptions.short
      return result;
    },
  });

  fieldRegistry.add('employee_role_tag_widget', FieldEmployeeRoleTags);

});

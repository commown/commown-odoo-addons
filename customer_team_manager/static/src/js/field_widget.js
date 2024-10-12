odoo.define("many2many_tags_help_widget", function (require) {
  "use strict";

  var ajax = require('web.ajax');
  var core = require('web.core');
  var FieldMany2ManyTags = require('web.relational_fields').FieldMany2ManyTags;
  var fieldRegistry = require('web.field_registry');

  ajax.loadXML('/customer_team_manager/static/src/xml/field_widget_template.xml', core.qweb);

  var FieldMany2ManyTagsHelp = FieldMany2ManyTags.extend({
    tag_template: "FieldMany2ManyTagsHelp",
    fieldsToFetch: {
        display_name: {type: 'char'},
        description: {type: 'char'},
    },
  });

  fieldRegistry.add('many2many_tags_help_widget', FieldMany2ManyTagsHelp);

});

odoo.define('commown.menu_settings', function (require) {
  'use strict';

  var session = require('web.session');
  var UserMenu = require('web.UserMenu');

  UserMenu.include({
    start: function () {
      this._super();

      if (session.is_in_group_user) {
        $(".customer-menu").remove();
      } else {
        $("a[data-menu='settings']").remove();
      }

    }
  });

});

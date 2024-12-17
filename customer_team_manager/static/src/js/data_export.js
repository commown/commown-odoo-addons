odoo.define('customer_team_manager.DataExport', function(require) {
  "use strict";

  var session = require('web.session');
  var DataExport = require('web.DataExport');

  DataExport.include({
    /*
      Overwride the export widget to simplify it for customer admins
    */
    start: function () {
      var deferred = this._super.apply(this, arguments);

      if (session.is_customer_admin) {
        // Make css customization easy to accomodate the UI:
        this.$el.addClass("js-customer-admin");

        // Reset css height to content instead of hard-js-coded 100%:
        this.$modal.find(".modal-content").css("height", "initial");
      }

      var self = this;
      return deferred.then(function () {
        self._opened.then(function () {
          // Automatically select the radio "compatible with import" button when the
          // UI is loaded, as the other choice is set in js and html by default:
          self.$import_compat_radios.filter("[value='yes']").click();
        });
      });
    },

  });

});

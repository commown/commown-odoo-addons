odoo.define("customer_team_manager.SearchView", function (require) {
    "use strict";

    var session = require("web.session");
    var SearchView = require("web.SearchView");

    SearchView.include({
        /*
      Disable the widget alltogether for customer admins
    */
        willStart: function () {
            this.options.disable_favorites = session.is_customer;
            return this._super();
        },
    });
});

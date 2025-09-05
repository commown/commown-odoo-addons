odoo.define("product_rental.ProductConfiguratorMixin", function (require) {
    "use strict";

    var publicWidget = require("web.public.widget");
    require("website_sale.website_sale");

    var variantIdEl = document.getElementById("variant_id_placeholder");

    publicWidget.registry.WebsiteSale.include({
        _onChangeCombination: function (ev, $parent, combination) {
            this._super.apply(this, arguments);
            if (variantIdEl !== null) {
                variantIdEl.textContent = combination.product_id;
            }
        },
    });
});

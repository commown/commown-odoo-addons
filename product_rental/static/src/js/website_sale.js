odoo.define("product_rental.VariantMixin", function (require) {
    "use strict";

    var VariantMixin = require("sale.VariantMixin");
    var publicWidget = require("web.public.widget");

    require("website_sale.website_sale");

    publicWidget.registry.WebsiteSale.include({
        _onChangeCombination: function (ev, $parent, combination) {
            this._super.apply(this, arguments);
            const $recurrent_payment_amount = $parent.find(
                ".oe_recurrent_payment_amount"
            );
            const ratio = parseFloat(
                $recurrent_payment_amount.data("recurrent-payment-ratio")
            );
            const price = this._priceToStr(combination.price / ratio);
            $recurrent_payment_amount.find(".oe_currency_value").html(price);
        },
    });

    return VariantMixin;
});

odoo.define("product_rental.OptionalProductsModal", function (require) {
    "use strict";

    const {
        OptionalProductsModal,
    } = require("@sale_product_configurator/js/product_configurator_modal");

    OptionalProductsModal.include({
        _onChangeCombination: function (ev, $parent, combination) {
            this._super.apply(this, arguments);
            const $recurrent_payment_amount = $parent.find(
                ".oe_recurrent_payment_amount"
            );
            const ratio = parseFloat(
                $recurrent_payment_amount.data("recurrent-payment-ratio")
            );
            const price = this._priceToStr(combination.price / ratio);
            $recurrent_payment_amount.find(".oe_currency_value").html(price);
        },
    });

    return OptionalProductsModal;
});

odoo.define("product_rental.ProductConfiguratorMixin", function (require) {
    "use strict";

    var ProductConfiguratorMixin = require("sale.ProductConfiguratorMixin");
    var sAnimations = require("website.content.snippets.animation");

    sAnimations.registry.WebsiteSale.include({
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

    return ProductConfiguratorMixin;
});

odoo.define("product_rental.OptionalProductsModal", function (require) {
    "use strict";

    var optionalProductModal = require("sale.OptionalProductsModal");

    optionalProductModal.include({
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

    return optionalProductModal;
});

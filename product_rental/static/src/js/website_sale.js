(function () {
    "use strict";

    function set_recurrent_price(priceToStr, $parent, combination) {
        const $recurrent_payment_amount = $parent.find(".oe_recurrent_payment_amount");

        if ($recurrent_payment_amount.length) {
            const ratio = parseFloat(
                $recurrent_payment_amount.data("recurrent-payment-ratio")
            );
            const price = priceToStr(combination.price / ratio);
            $recurrent_payment_amount.find(".oe_currency_value").html(price);
        }
    }

    odoo.define("product_rental.VariantMixin", function (require) {
        var VariantMixin = require("sale.VariantMixin");
        var publicWidget = require("web.public.widget");

        require("website_sale.website_sale");

        publicWidget.registry.WebsiteSale.include({
            _onChangeCombination: function (ev, $parent, combination) {
                this._super.apply(this, arguments);
                set_recurrent_price(this._priceToStr, $parent, combination);
            },
        });

        return VariantMixin;
    });

    odoo.define("product_rental.OptionalProductsModal", function (require) {
        const {
            OptionalProductsModal,
        } = require("@sale_product_configurator/js/product_configurator_modal");

        OptionalProductsModal.include({
            _onChangeCombination: function (ev, $parent, combination) {
                this._super.apply(this, arguments);
                set_recurrent_price(this._priceToStr, $parent, combination);
            },
        });

        return OptionalProductsModal;
    });
})();

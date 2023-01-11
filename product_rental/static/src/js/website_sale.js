odoo.define('product_rental.ProductConfiguratorMixin', function (require) {
'use strict';

var ProductConfiguratorMixin = require('sale.ProductConfiguratorMixin');
var sAnimations = require('website.content.snippets.animation');

sAnimations.registry.WebsiteSale.include({
    _onChangeCombination: function (ev, $parent, combination){
        this._super.apply(this, arguments);
        let $rental_price = $parent.find('.oe_rental_price');
        let ratio = parseFloat($rental_price.data('rental-ratio'));
        let price = this._priceToStr(combination.price / ratio);
        $rental_price.find(".oe_currency_value").html(price);
    }
});

return ProductConfiguratorMixin;

});


odoo.define('product_rental.OptionalProductsModal', function (require) {
'use strict';

var optionalProductModal = require('sale.OptionalProductsModal');

optionalProductModal.include({
    _onChangeCombination: function (ev, $parent, combination){
        this._super.apply(this, arguments);
        let $rental_price = $parent.find('.oe_rental_price');
        let ratio = parseFloat($rental_price.data('rental-ratio'));
        let price = this._priceToStr(combination.price / ratio);
        $rental_price.find(".oe_currency_value").html(price);
    }
});

return optionalProductModal;

});

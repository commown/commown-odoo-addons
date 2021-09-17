odoo.define('product_rental.ProductConfiguratorMixin', function (require) {
'use strict';

var ProductConfiguratorMixin = require('sale.ProductConfiguratorMixin');
var sAnimations = require('website.content.snippets.animation');

var $rental_price = $('.oe_website_sale .oe_rental_price');
var ratio = parseFloat($rental_price.data('rental-ratio'));

sAnimations.registry.WebsiteSale.include({
    _onChangeCombination: function (ev, $parent, combination){
        this._super.apply(this, arguments);
        $rental_price.html(this._priceToStr(combination.price /= ratio));
    }
});

return ProductConfiguratorMixin;

});

odoo.define('product_rental.ProductConfiguratorMixin', function (require) {
'use strict';

var ProductConfiguratorMixin = require('sale.ProductConfiguratorMixin');
var sAnimations = require('website.content.snippets.animation');

var variantIdEl = document.getElementById('variant_id_placeholder');

sAnimations.registry.WebsiteSale.include({
    _onChangeCombination: function (ev, $parent, combination) {
        this._super.apply(this, arguments);
        if(variantIdEl !== null) {
          variantIdEl.textContent = combination.product_id;
        }
    }
});

return ProductConfiguratorMixin;

});

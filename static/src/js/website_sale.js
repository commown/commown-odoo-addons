odoo.define('product_rental.website_sale', function(require) {
    "use strict";

    function adjustProductPriceToLeasePeriod($container, ratio) {
        // Adjust the product prices included in the DOM structure under
        // the `$container` jQuery DOM object by dividing it by given ratio
        // (which must be a number)
        //
        console.info('Adjusting price in', $container, 'by a factor of', ratio);

        var $variantHolder = $('ul[data-attribute_value_ids]', $container);
        if ($variantHolder.data('oe_rental_price_computed')) {
            console.warn('Rental price already computed!');
            return;
        }

        var variantIds = $variantHolder.data("attribute_value_ids");
        console.debug('variants before:', JSON.parse(JSON.stringify(variantIds)));
        for (var key in variantIds) {
            variantIds[key][2] = variantIds[key][2] / (ratio || 1);
        }
        console.debug('variants after:', JSON.parse(JSON.stringify(variantIds)));

        $variantHolder.data('oe_rental_price_computed', true);
    }

    $(function() {
        $('.oe_website_sale').each(function() {
            var $this = $(this);
            var ratio = $('.oe_rental_price', $this).data('rental-ratio');
            if ($this.find('.oe_rental_price').length > 0 &&
                    ratio !== undefined) {
                adjustProductPriceToLeasePeriod($this, parseFloat(ratio));
            }
        });
    });

});

odoo.define('commown.website_sale', function(require) {
    "use strict";

    $('.oe_website_sale').each(function() {
        $(this).on('change', 'input.js_variant_change, select.js_variant_change, ul[data-attribute_value_ids]', function (ev) {
            var $ul = $(ev.target).closest('.js_add_cart_variants');
            var $parent = $ul.closest('.js_product');
            var variant_ids = $ul.data("attribute_value_ids");
            var values = [];
            var unchanged_values = $parent.find('div.oe_unchanged_value_ids').data('unchanged_value_ids') || [];

            $parent.find('input.js_variant_change:checked, select.js_variant_change').each(function () {
                values.push(+$(this).val());
            });
            values =  values.concat(unchanged_values);

            for (var k in variant_ids) {
                if (_.isEmpty(_.difference(variant_ids[k][1], values))) {
                    $('.variant_id_placeholder').text(variant_ids[k][0])
                    break;
                }
            }
        });
    });

});

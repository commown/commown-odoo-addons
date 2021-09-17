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

    function toggleValueMatchClass(widget) {
        // Toggle the "attribute-value-match" css class on all elements of
        // the page that match the js-attribute-dependant and the
        // js-attribute-[product_id]-[attribute_id] selectors corresponding
        // to the attribute selected in passed widget argument.
        // Sample HTML usage:
        // <p class="js-attribute-1-6 js-attribute-1-6-94 attribute-show">
        //   Content only visible when value of attribute 6 of product 1 is 94
        // </p>
        var matchValue = 'js-' + widget.name + '-' + widget.value;
        $('.js-' + widget.name).each(function(index, el) {
            var $el = $(el);
            $el.toggleClass('attribute-value-match', $el.hasClass(matchValue));
        });
    }

    $('.oe_website_sale').each(function() {

        var oe_website_sale = this;

        console.debug('Setting up automatic css change on variant choice');

        var widgetSelector = 'input.js_variant_change,select.js_variant_change';

        $(widgetSelector, oe_website_sale).each(function(index, el) {
            toggleValueMatchClass(el);
        });
        $(oe_website_sale).on('change', widgetSelector, function (ev) {
            toggleValueMatchClass(ev.target);
        });

    });

});

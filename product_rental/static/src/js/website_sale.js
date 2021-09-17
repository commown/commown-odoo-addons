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

  // Remove me ASAP!
  // This code updates the deposit amount when the variant selector changes.
  // It should be much better in v12...

  var base = require('web_editor.base');
  var utils = require('web.utils');
  var core = require('web.core');
  var _t = core._t;

  function price_to_str(price) {
    var l10n = _t.database.parameters;
    var precision = 2;

    if ($(".decimal_precision").length) {
      precision = parseInt($(".decimal_precision").last().data('precision'));
      if (!precision) { precision = 0; }
    }
    var formatted = _.str.sprintf('%.' + precision + 'f', price).split('.');
    formatted[0] = utils.insert_thousand_seps(formatted[0]);
    return formatted.join(l10n.decimal_point);
  }

  $('.oe_website_sale').on('change', 'input.js_variant_change, select.js_variant_change, ul[data-attribute_value_ids]', function (ev) {
    var $ul = $(ev.target).closest('.js_add_cart_variants');
    var $parent = $ul.closest('.js_product');
    var variant_ids = $ul.data("attribute_value_ids");
    var values = [];
    var unchanged_values = $parent.find('div.oe_unchanged_value_ids').data('unchanged_value_ids') || [];
    var ratio = $('.oe_website_sale .oe_rental_price').data('rental-ratio');

    $parent.find('input.js_variant_change:checked, select.js_variant_change').each(function () {
      values.push(+$(this).val());
    });
    values =  values.concat(unchanged_values);

    for (var k in variant_ids) {
      if (_.isEmpty(_.difference(variant_ids[k][1], values))) {
        $.when(base.ready()).then(function() {
          $(".oe_deposit_price .oe_currency_value").html(price_to_str(variant_ids[k][2]*ratio))
        });
        break;
      }
    }
  })

});

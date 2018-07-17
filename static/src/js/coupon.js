odoo.define('website_sale_coupon.coupon', function(require) {
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');
    var qweb = core.qweb;
    ajax.loadXML('/website_sale_coupon/static/src/xml/coupon_templates.xml',
                 qweb);

    function displayCoupon(coupon) {
        var $coupon = $(qweb.render(
            'coupon.used', {'code': coupon.code, 'descr': coupon.descr}));
        var $placeholder = $('#coupons-placeholder');
        if ($placeholder.find('dl').length == 0) {
            $('<dl class="dl-horizontal"/>').appendTo($placeholder);
        }
        $coupon.appendTo($placeholder.find('dl'));
    }

    ajax.jsonRpc('/website_sale_coupon/reserved_coupons', 'call')
        .done(function(result) {
            console.log('used_coupons success! result=%o', result);
            result.forEach(function(coupon) {displayCoupon(coupon);});
        });

    $(function() {  // wait for the form to be inserted in the DOM

        var $form = $('form#coupon_input');

        $form.on('submit', function(ev) {
            // Only executed on the cart page, where the coupon input
            // form appears
            ev.preventDefault();
            ev.stopPropagation();

            var $button = $form.find(':submit');
            var $spinner = $button.find('i[class~="fa"]');
            var $input = $form.find('input[name="coupon_code"]');

            $button.attr('disabled', 'disabled');
            $spinner.show();

            var code = $input.val();

            ajax.jsonRpc('/website_sale_coupon/reserve_coupon', 'call',
                         {code: code})

                .done(function(result) {
                    $button.removeAttr('disabled');
                    $spinner.hide();
                    console.log('use_coupon success! result=%o', result);
                    if(result.success) {
                        displayCoupon(result.descr);
                        $input.val('');
                    } else {
                        $(qweb.render('coupon.wrong', {'code': code}))
                            .appendTo($('body')).modal();
                    }
                })

                .fail(function(_, result) {
                    $button.removeAttr('disabled');
                    $spinner.hide();
                    console.log('use_coupon failed! result=%o', result);
                });

            return false;
        });

        $form.find(':submit').removeAttr('disabled');

    });

});

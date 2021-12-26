odoo.define('website_sale_coupon.coupon', function(require) {
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');
    var qweb = core.qweb;
    var templates = ajax.loadXML(
      '/website_sale_coupon/static/src/xml/coupon_templates.xml',
      qweb
    );

    function displayCoupons(coupons) {
        var $dl = $('<dl class="dl-horizontal"/>').appendTo(
            $('#coupons-placeholder').empty()
        );
        coupons.forEach(function(coupon) {
            $(qweb.render('coupon.used',
                          {'name': coupon.name, 'descr': coupon.descr}))
                .appendTo($dl);
        });
    }

    templates.done(function() {
      ajax.jsonRpc('/website_sale_coupon/reserved_coupons', 'call')
        .done(function(result) {
            console.log('used_coupons success! result=%o', result);
            displayCoupons(result);
        });
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
                        $input.val('');
                        displayCoupons(result.coupons);
                        $(qweb.render('coupon.valid', {'code': code}))
                            .appendTo($('body')).modal();
                    } else {
                        $(qweb.render(
                          'coupon.wrong',
                          {'code': code, 'reason': result["reason"]}
                        )).appendTo($('body')).modal();
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

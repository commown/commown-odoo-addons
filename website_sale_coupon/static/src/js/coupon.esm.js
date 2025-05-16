/** @odoo-module */

import publicWidget from "web.public.widget";
import {qweb} from "web.core";

function displayCoupons(coupons) {
    var $dl = $("<dl/>").appendTo($("#coupons-placeholder").empty());
    coupons.forEach(function (coupon) {
        $(
            qweb.render("coupon.used", {name: coupon.name, descr: coupon.descr})
        ).appendTo($dl);
    });
}

publicWidget.registry.CouponForm = publicWidget.Widget.extend({
    selector: "#coupon-form",

    events: {
        "submit form#coupon_input": "validateCoupon",
    },

    init: function () {
        this._super(...arguments);
        this.$form = $("form#coupon_input");
    },

    displayCoupons: displayCoupons,

    start: function () {
        this.$form.find(":submit").removeAttr("disabled");
    },

    validateCoupon: function (ev) {
        // Only executed on the cart page, where the coupon input
        // form appears
        ev.preventDefault();
        ev.stopPropagation();

        var $button = this.$form.find(":submit");
        var $spinner = $button.find('i[class~="fa"]');
        var $input = this.$form.find('input[name="coupon_code"]');

        $button.attr("disabled", "disabled");
        $spinner.show();

        var self = this;
        var code = $input.val();

        this._rpc({
            route: "/website_sale_coupon/reserve_coupon",
            params: {code: code},
        }).then(
            function (result) {
                // Done function
                $button.removeAttr("disabled");
                $spinner.hide();
                console.debug("reserve_coupon call returned %o", result);
                if (result.success) {
                    $input.val("");
                    self.displayCoupons(result.coupons);
                    $(qweb.render("coupon.valid", {code: code}))
                        .appendTo($("body"))
                        .modal("show");
                } else {
                    $(
                        qweb.render("coupon.wrong", {
                            code: code,
                            reason: result.reason,
                        })
                    )
                        .appendTo($("body"))
                        .modal("show");
                }
            },
            function (_, result) {
                // Failed function
                $button.removeAttr("disabled");
                $spinner.hide();
                console.debug("reserve_coupon call failed! result=%o", result);
            }
        );

        return false;
    },
});

publicWidget.registry.InitCouponPlaceholder = publicWidget.Widget.extend({
    selector: "#coupons-placeholder",

    displayCoupons: displayCoupons,

    start: function () {
        var self = this;
        this._rpc({
            route: "/website_sale_coupon/reserved_coupons",
        })
            .then(function (result) {
                console.debug("reserved_coupons call returned %o", result);
                self.displayCoupons(result);
            })
            .catch((error) => {
                console.log("An error occurred: ", error.message);
            });
    },
});

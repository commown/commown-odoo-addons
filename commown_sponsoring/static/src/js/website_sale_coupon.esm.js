/** @odoo-module */

import publicWidget from "web.public.widget";
import {qweb} from "web.core";

publicWidget.registry.InitCouponPlaceholder.include({
    start: function () {
        this._rpc({route: "/commown_sponsoring/check_coupons"}).then(function (result) {
            console.debug("/commown_sponsoring/check_coupons result : %o", result);
            if (result.removed_coupon) {
                $(qweb.render("coupon.wrong", {reason: result.reason}))
                    .appendTo($("body"))
                    .modal("show");
            }
        });
        this._super.apply(this, arguments);
    },
});

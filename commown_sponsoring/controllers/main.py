from odoo import _, http
from odoo.http import request

from odoo.addons.web.controllers.home import Home
from odoo.addons.website_sale_coupon.controllers import main


class SponsorWebsiteController(Home):
    def _login_redirect(self, uid, redirect=None):
        "After logging in, we run checks on any reserved sponsor code"
        order = request.website.sale_get_order()
        order_coupons = order.reserved_coupons()
        reserved_sponsor_coupon = order_coupons and order_coupons.filtered(
            "campaign_id.sponsor_partner_id"
        )
        if order and reserved_sponsor_coupon:
            code = reserved_sponsor_coupon.code
            unlink_code = False

            # We check if the customer has already used a sponsor code previously
            partner = request.env.user.partner_id
            if partner.already_used_sponsor_code(order):
                unlink_code = True
                request.session[f"{order.id}-cancelled_coupon"] = code

            # Check if the reserved sponsor code is still valid (ie. related partner still has active contracts)
            sponsor_partner = reserved_sponsor_coupon.campaign_id.sponsor_partner_id
            if not sponsor_partner.is_sponsor_code_active():
                unlink_code = True
                request.session[f"{order.id}-invalid_coupon"] = code

            if unlink_code:
                reserved_sponsor_coupon.unlink()

        return super()._login_redirect(uid, redirect)


class SponsorCouponController(main.WebsiteSaleCouponController):
    @http.route(
        "/commown_sponsoring/check_coupons",
        type="json",
        auth="public",
        website=True,
    )
    def _check_coupons(self):
        "Checking if a coupon was placed in the session values"
        res = {"removed_coupon": None}
        order = request.website.sale_get_order()

        if f"{order.id}-cancelled_coupon" in request.session:
            res.update(
                {
                    "removed_coupon": request.session.pop(
                        f"{order.id}-cancelled_coupon"
                    ),
                    "reason": _(
                        "We removed the reserved sponsorship code, as you "
                        "already used another one on a previous order."
                    ),
                }
            )
        elif f"{order.id}-invalid_coupon" in request.session:
            res.update(
                {
                    "removed_coupon": request.session.pop(f"{order.id}-invalid_coupon"),
                    "reason": _(
                        "We removed the reserved sponsorship code, as it is no longer active."
                    ),
                }
            )

        return res

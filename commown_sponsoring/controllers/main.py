from odoo.http import request

from odoo.addons.web.controllers.home import Home


class SponsorWebsiteController(Home):
    def _login_redirect(self, uid, redirect=None):
        "After logging in, we run checks on any reserved sponsor code"
        order = request.website.sale_get_order()
        order_coupons = order.reserved_coupons()
        reserved_sponsor_coupon = order_coupons and order_coupons.filtered(
            "campaign_id.sponsor_partner_id"
        )
        if order and reserved_sponsor_coupon:
            # We check if the customer has already used a sponsor code previously
            partner = request.env.user.partner_id
            if partner.already_used_sponsor_code(order):
                reserved_sponsor_coupon.unlink()

        return super()._login_redirect(uid, redirect)

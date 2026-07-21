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
            unlink_code = False

            # We check if the customer has already used a sponsor code previously
            partner = request.env.user.partner_id
            if partner.already_used_sponsor_code(order):
                unlink_code = True

            # Check if the reserved sponsor code is still valid (ie. related partner still has active contracts)
            sponsor_partner = reserved_sponsor_coupon.campaign_id.sponsor_partner_id
            if not sponsor_partner.is_sponsor_code_active():
                unlink_code = True

            if unlink_code:
                reserved_sponsor_coupon.unlink()

        return super()._login_redirect(uid, redirect)

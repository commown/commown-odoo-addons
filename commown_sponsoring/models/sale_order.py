from odoo import _, models

from odoo.addons.website_sale_coupon.models.sale_order import CouponError


class SponsoringSaleOrder(models.Model):
    _inherit = "sale.order"

    def reserve_coupon(self, code):
        err_msg = _("You have already used a sponsoring code")
        sponsor_campaign = (
            self.env["coupon.campaign"]
            .sudo()
            .search(
                [
                    ("name", "=", code.upper()),
                    ("is_without_coupons", "=", True),
                    ("sponsor_partner_ids", "!=", False),
                ]
            )
        )

        if self and sponsor_campaign:
            sponsor_partner = sponsor_campaign.sponsor_partner_id
            if not sponsor_partner.is_sponsor_code_active():
                raise CouponError(_("This sponsoring code is currently inactive."))

            # If the customer already has used another sponsoring code,
            # either in this or another order, we refuse the coupon.
            if self.reserved_coupons().mapped("campaign_id.sponsor_partner_id"):
                raise CouponError(_("%s in this order.", err_msg))

            if self.partner_id.already_used_sponsor_code(self):
                raise CouponError(_("%s on a previous order.", err_msg))

        return super().reserve_coupon(code)

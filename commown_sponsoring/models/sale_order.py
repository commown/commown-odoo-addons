from odoo import _, models

from odoo.addons.website_sale_coupon.models.sale_order import CouponError


class SponsoringSaleOrder(models.Model):
    _inherit = "sale.order"

    def reserve_coupon(self, code):
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

        return super().reserve_coupon(code)

from odoo import fields, models


class CouponCreateMultipleWizard(models.TransientModel):
    _name = "website_sale_coupon.create_multiple_coupons_wizard"
    _description = "Create an arbitrary number of coupon of the same campain"

    campaign_id = fields.Many2one(
        "coupon.campaign",
        string="Campaign",
        required=True,
    )

    coupon_nb = fields.Integer(
        "Number of coupon to create",
        required=True,
    )

    def create_multiple_coupons(self):
        coupons = [{"campaign_id": self.campaign_id.id} for i in range(self.coupon_nb)]
        self.env["coupon.coupon"].create(coupons)

from odoo import _, api, fields, models


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
        created_coupons = self.env["coupon.coupon"].create(coupons)
        return created_coupons.ids

    @api.multi
    def button_create_and_open_coupons(self):
        self.ensure_one()
        created_coupons_ids = self.create_multiple_coupons()
        return {
            "name": _("Coupons"),
            "domain": [("id", "in", created_coupons_ids)],
            "type": "ir.actions.act_window",
            "view_mode": "tree,form",
            "res_model": "coupon.coupon",
        }

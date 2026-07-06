from odoo import fields, models


class SponsoringResPartner(models.Model):
    _inherit = "res.partner"

    sponsor_campaign_id = fields.Many2one(comodel_name="coupon.campaign", readonly=True)
    sponsor_code = fields.Char(
        string="Sponsor code", related="sponsor_campaign_id.name"
    )

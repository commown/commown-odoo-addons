from odoo import fields, models


class SponsoringCouponCampaign(models.Model):
    _inherit = "coupon.campaign"

    sponsor_partner_ids = fields.One2many(
        comodel_name="res.partner", inverse_name="sponsor_campaign_id", readonly=True
    )
    sponsor_partner_id = fields.Many2one(
        comodel_name="res.partner", compute="_compute_sponsor_partner"
    )

    def _compute_sponsor_partner(self):
        for campaign in self:
            campaign.sponsor_partner_id = (
                campaign.sponsor_partner_ids and campaign.sponsor_partner_ids[0]
            )

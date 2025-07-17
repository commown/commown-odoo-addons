from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _followup_entity_title_prefix(self, contract=None, secondary_index=None):
        title = super()._followup_entity_title_prefix(
            contract=contract, secondary_index=secondary_index
        )
        coupons = self.used_coupons()
        if coupons:
            title += " - COUPON: " + ", ".join(coupons.mapped("campaign_id.name"))
        return title

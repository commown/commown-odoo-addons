from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def get_holding(self):
        self.ensure_one()
        holding = self.commercial_partner_id
        while holding.parent_id:
            holding = holding.parent_id.commercial_partner_id
        return holding

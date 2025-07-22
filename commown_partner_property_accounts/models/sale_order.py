from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        self.partner_id._create_receivable_account()
        return super().action_confirm()

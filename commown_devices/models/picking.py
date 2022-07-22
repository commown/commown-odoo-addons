from odoo import _, fields, models
from odoo.exceptions import UserError

from .common import _force_picking_date


class StockPicking(models.Model):
    _inherit = "stock.picking"

    contract_id = fields.Many2one("contract.contract", string="Contract")

    def action_set_date_done_to_scheduled(self):
        self.ensure_one()

        if not self.state == "done":
            raise UserError(_("Transfer must be done to use this action"))

        _force_picking_date(self, self.scheduled_date)

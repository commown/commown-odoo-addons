from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .common import _force_picking_date


class StockPicking(models.Model):
    _inherit = "stock.picking"

    contract_ids = fields.Many2many(
        "contract.contract",
        string="Contract",
        compute="_compute_contract_ids",
        store=False,
    )

    def _compute_contract_ids(self):
        for record in self:
            record.contract_ids = self.move_lines.mapped("contract_id")

    @api.multi
    def action_set_date_done_to_scheduled(self):
        for rec in self:
            if not rec.state == "done":
                raise UserError(_("Transfer must be done to use this action"))

            _force_picking_date(rec, rec.scheduled_date)

from odoo import _, fields, models
from odoo.exceptions import UserError

from .common import _force_scrap_date


class StockScrap(models.Model):
    _inherit = "stock.scrap"

    contract_id = fields.Many2one("contract.contract", string="Contract")

    def action_set_date_done_to_move_line_date(self):
        for rec in self:
            if not rec.state == "done":
                raise UserError(_("Scrap must be done to use this action"))

            _force_scrap_date(rec, rec.move_id.move_line_ids.date)

    def action_validate(self):
        return super(
            StockScrap,
            self.with_context(default_contract_id=self.contract_id.id),
        ).action_validate()

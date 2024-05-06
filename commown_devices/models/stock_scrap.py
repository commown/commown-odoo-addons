from odoo import _, api, models
from odoo.exceptions import UserError

from .common import _force_scrap_date


class StockScrap(models.Model):
    _inherit = "stock.scrap"

    @api.multi
    def action_set_date_done_to_expected(self):
        for rec in self:
            if not rec.state == "done":
                raise UserError(_("Scrap must be done to use this action"))

            _force_scrap_date(rec, rec.date_expected)

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    contract_id = fields.Many2one("contract.contract", string="Contract")

    def _action_confirm(self, merge=True, merge_into=False):
        if self.env.context.get("dont_merge_moves", False):
            merge = False

        return super()._action_confirm(merge=merge, merge_into=merge_into)

    def _action_done(self):
        res = super()._action_done()
        self.update_lot_location()
        return res

    def update_lot_location(self):
        for rec in self:
            lot_ids = rec.move_line_ids.mapped("lot_id")
            if rec.contract_id and lot_ids:
                lot_nb = len(lot_ids)
                if lot_nb > 1:
                    _logger.warning(
                        "%s lots found on move %s. Associating %s new lot to contract %s",
                        lot_nb,
                        rec.id,
                        lot_nb,
                        rec.contract_id.id,
                    )
                contract_loc = rec.contract_id.partner_id.get_customer_location()
                if rec.location_dest_id == contract_loc:
                    lot_ids.update({"contract_id": rec.contract_id})
                elif (
                    rec.location_id == contract_loc
                    and lot_ids.mapped("contract_id") == rec.contract_id
                ):
                    lot_ids.update({"contract_id": False})

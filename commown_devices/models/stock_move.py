import logging

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    contract_id = fields.Many2one("contract.contract", string="Contract")

    def _action_confirm(self, merge=True, merge_into=False):
        """Override the method so moves are merged or not depending on the context"""

        if self.env.context.get("dont_merge_moves", False):
            merge = False

        return super()._action_confirm(merge=merge, merge_into=merge_into)

    def _action_done(self):
        """Overrride the method to trigger update_lot_contract method"""

        res = super()._action_done()
        self.update_lot_contract()
        return res

    def update_lot_contract(self):
        """If the move is associated with a contract create or delete relation
        between lot and contract depending on the move destination.
        """
        for rec in self:
            lots = rec.mapped("move_line_ids.lot_id")
            assert (
                len(lots.mapped("contract_id")) < 2
            ), "More than one contract on move %s lots" % (rec.id)

            if rec.contract_id and lots:

                if len(lots.mapped("contract_id")) > 1:
                    msg = _("More than one contract on move %s lots")
                    _logger.warning(msg, rec.id)

                contract_loc = rec.contract_id.partner_id.get_customer_location()

                if rec.location_dest_id == contract_loc:
                    lots.update({"contract_id": rec.contract_id})

                elif rec.location_id == contract_loc:

                    if lots.mapped("contract_id") != rec.contract_id:
                        raise UserError(
                            "Inconsistent move (id: %s, picking id: %s) contract (id: %s) and lot contract (id: %s)"
                            % (
                                rec.id,
                                rec.picking_id.id,
                                rec.contract_id.id,
                                lots.mapped("contract_id"),
                            )
                        )

                    lots.update({"contract_id": False})

                else:
                    raise UserError(
                        "Inconsistent move (id: %s, picking id: %s) and contract (id: %s) locations"
                        % (rec.id, rec.picking_id.id, rec.contract_id.id)
                    )

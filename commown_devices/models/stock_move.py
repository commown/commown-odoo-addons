import logging

from odoo import _, fields, models
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
        no_raise = self.env.context.get("no_raise_in_update_lot_contract", False)

        def _error(rec, err_msg):
            err_args = {
                "move_id": rec.id,
                "picking_id": rec.picking_id.id,
                "contract_id": rec.contract_id.id,
                "lot_contract_id": rec.mapped("move_line_ids.lot_id.contract_id").ids,
            }
            if no_raise:
                _logger.error(err_msg, err_args)
            else:
                raise UserError(err_msg % err_args)

        for rec in self:
            lots = rec.mapped("move_line_ids.lot_id")

            if rec.contract_id and lots:

                if len(lots.mapped("contract_id")) > 1:
                    msg = _("More than one contract on move %s lots")
                    _logger.warning(msg, rec.id)

                contract_loc = rec.contract_id.partner_id.get_customer_location()

                if not contract_loc:
                    _error(
                        rec, "No contract location for contract (id: %(contract_id)s)"
                    )

                if rec.location_dest_id.has_partner_child_of(contract_loc):
                    lots.update({"contract_id": rec.contract_id})

                elif rec.location_id.has_partner_child_of(contract_loc):
                    if lots.mapped("contract_id") != rec.contract_id:
                        msg = _(
                            "Inconsistent move (id: %(move_id)s, picking id:"
                            " %(picking_id)s) contract (id: %(contract_id)s) and lot"
                            " contract (id: %(lot_contract_id)s)"
                        )
                        _error(rec, msg)

                    lots.update({"contract_id": False})

                else:
                    msg = _(
                        "Inconsistent locations between move (id: %(move_id)s, picking"
                        " id: %(picking_id)s) and contract (id: %(contract_id)s)"
                    )
                    _error(rec, msg)

from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    is_contract_in = fields.Boolean(compute="_compute_is_contract_in", store=False)
    show_validate_picking = fields.Boolean(
        compute="_compute_show_validate_picking", store=False
    )

    def _compute_is_contract_in(self):
        for rec in self:
            contract = rec.move_id.contract_id
            if contract:
                loc = contract.partner_id.get_customer_location()
                rec.is_contract_in = loc == rec.location_dest_id
            else:
                rec.is_contract_in = False

    @api.onchange("move_id.picking_id.state")
    def _compute_show_validate_picking(self):
        "Onchange is used by UI to hide the validate button once picking is validated"
        for rec in self:
            rec.show_validate_picking = (
                rec.move_id.picking_id and rec.move_id.picking_id.state == "assigned"
            )

    def action_validate_linked_picking(self):
        self.move_id.picking_id.button_validate()

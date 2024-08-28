from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    is_contract_in = fields.Boolean(compute="_compute_is_contract_in", store=False)
    show_validate_picking = fields.Boolean(
        compute="_compute_show_validate_picking", store=False
    )

    origin = fields.Char(string="origin", compute="_compute_origin", store=False)

    def _compute_is_contract_in(self):
        for rec in self:
            contract = rec.move_id.contract_id
            if contract:
                loc = contract.partner_id.get_customer_location()
                rec.is_contract_in = loc == rec.location_dest_id
            else:
                rec.is_contract_in = False

    @api.depends("move_id.picking_id", "move_id.scrap_ids")
    def _compute_origin(self):
        for rec in self:
            parent = rec._get_parent()
            if parent is not None:
                rec.origin = parent.origin

    @api.onchange("move_id.picking_id.state")
    def _compute_show_validate_picking(self):
        "Onchange is used by UI to hide the validate button once picking is validated"
        for rec in self:
            rec.show_validate_picking = (
                rec.move_id.picking_id and rec.move_id.picking_id.state == "assigned"
            )

    def action_open_parent(self):
        parent = self.move_id.scrap_ids or self.move_id.picking_id
        if not parent:
            return None
        else:
            parent = parent[0]
            return {
                "name": "Source",
                "type": "ir.actions.act_window",
                "view_type": "form",
                "view_mode": "form",
                "res_model": parent._name,
                "res_id": parent.id,
                "target": "current",
            }

    def action_validate_linked_picking(self):
        unvalidated_contract_ml = self.move_id.contract_id.move_line_ids.filtered(
            lambda ml: ml.state == "assigned"
        )
        if len(unvalidated_contract_ml) > 1:
            return {
                "type": "ir.actions.act_window",
                "name": "Message",
                "res_model": "move.line.validation.wizard",
                "view_type": "form",
                "view_mode": "form",
                "target": "new",
                "context": {"default_move_line_id": self.id},
            }
        else:
            self.move_id.picking_id.button_validate()

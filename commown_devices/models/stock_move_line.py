from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    is_contract_in = fields.Boolean(compute="_compute_is_contract_in", store=False)
    show_validate_picking = fields.Boolean(
        compute="_compute_show_validate_picking", store=False
    )

    origin_label = fields.Char(
        string="Origin",
        help="Used by commown_devices to retrieve a move line's origin resource",
        compute="_compute_origin_label",
        store=False,
    )

    def _get_parent(self):
        return self.move_id.scrap_ids or self.move_id.picking_id

    def _compute_is_contract_in(self):
        for rec in self:
            contract = rec.move_id.contract_id
            if contract:
                loc = contract.partner_id.get_customer_locations(
                    contract.stock_ownership
                )
                rec.is_contract_in = loc == rec.location_dest_id
            else:
                rec.is_contract_in = False

    @api.depends("move_id.picking_id", "move_id.scrap_ids")
    def _compute_origin_label(self):
        for rec in self:
            rec.origin_label = rec._get_parent().origin_document_model_name

    def _compute_show_validate_picking(self):
        for rec in self:
            rec.show_validate_picking = (
                rec.move_id.picking_id and rec.move_id.picking_id.state == "assigned"
            )

    def action_open_parent(self):
        parent = self._get_parent()
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

    def action_open_parent_origin(self):
        parent = self._get_parent()
        if not parent:
            return None
        else:
            parent_origin = parent[0].origin_document()
            if parent_origin:
                return {
                    "name": "Source",
                    "type": "ir.actions.act_window",
                    "view_type": "form",
                    "view_mode": "form",
                    "res_model": parent_origin._name,
                    "res_id": parent_origin.id,
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

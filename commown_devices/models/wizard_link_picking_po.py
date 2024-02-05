import json

from odoo import api, fields, models


class MovePoLinkLine(models.TransientModel):
    _name = "move.po.link.line"
    _description = "Describe a relation between a stock move and a purchase order line"

    wizard_id = fields.Many2one(
        "picking.po.link.wizard",
        string="Picking Po wizard",
    )

    move_id = fields.Many2one(
        "stock.move",
        string="Stock move",
        required=True,
    )

    move_product_name = fields.Char(
        "Move product's name",
        readonly=True,
        store=False,
    )

    purchase_line_id = fields.Many2one(
        "purchase.order.line",
        string="Purchase order line",
    )

    purchase_line_id_domain = fields.Char(
        compute="_compute_purchase_line_id_domain",
        readonly=True,
        store=False,
    )

    @api.multi
    @api.depends("wizard_id.po_id")
    def _compute_purchase_line_id_domain(self):
        for rec in self:
            rec.purchase_line_id_domain = json.dumps(
                [("order_id", "=", rec.wizard_id.po_id.id)]
            )


class POInvoiceLinkWizard(models.TransientModel):
    _name = "picking.po.link.wizard"
    _description = "Wizard to link picking to purchase order"

    picking_id = fields.Many2one(
        "stock.picking",
        string="Picking",
        required=True,
    )

    po_id = fields.Many2one(
        "purchase.order",
        string="Select purchase order line from this purchase order",
        default=lambda self: self.env["stock.picking"]
        .browse(self.env.context.get("active_ids", []))
        .purchase_id,
    )

    link_line_ids = fields.One2many(
        "move.po.link.line",
        "wizard_id",
        string="Move to purchase_line link",
        default=lambda self: self._default_link_line_ids(),
    )

    def _default_link_line_ids(self):
        picking_id = self.env["stock.picking"].browse(
            self.env.context.get("active_ids", [])
        )

        return [
            (0, 0, {"move_id": line.id, "move_product_name": line.product_id.name})
            for line in picking_id.move_lines
            if not line.purchase_line_id
        ]

    @api.onchange("picking_id")
    def _compute_po_domain(self):
        if self.picking_id.partner_id:
            pid = self.picking_id.partner_id.commercial_partner_id.id
            return {
                "domain": {
                    "po_id": [
                        (
                            "partner_id.commercial_partner_id",
                            "=",
                            pid,
                        ),
                    ]
                }
            }

    def action_assign_po(self):
        for link in self.link_line_ids:
            link.move_id.purchase_line_id = link.purchase_line_id
        self.picking_id.purchase_id = self.po_id
        self.picking_id.origin = self.po_id.name

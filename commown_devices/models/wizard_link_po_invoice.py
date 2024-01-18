import json

from odoo import api, fields, models


class POInvoiceLinkLine(models.TransientModel):
    _name = "po.invoice.link.line"
    _description = "Describe a relation between a po_line and an invoice line"

    wizard_id = fields.Many2one(
        "po.invoice.link.wizard",
        string="Po invoice wizard",
    )

    po_line_id = fields.Many2one(
        "purchase.order.line",
        string="Purchase order line",
        required=True,
    )

    invoice_line_id = fields.Many2one(
        "account.invoice.line",
        string="Invoice lines",
    )

    invoice_line_id_domain = fields.Char(
        compute="_compute_invoice_line_id_domain",
        readonly=True,
        store=False,
    )

    @api.multi
    @api.depends("wizard_id.invoice_id")
    def _compute_invoice_line_id_domain(self):
        for rec in self:
            rec.invoice_line_id_domain = json.dumps(
                [("invoice_id", "=", rec.wizard_id.invoice_id.id)]
            )


class POInvoiceLinkWizard(models.TransientModel):
    _name = "po.invoice.link.wizard"
    _description = "Wizard to link purchase order line to invoices lines"

    po_id = fields.Many2one(
        "purchase.order",
        string="Purchase order",
        required=True,
    )

    invoice_id = fields.Many2one(
        "account.invoice",
        string="Select invoice line from this invoice",
    )

    link_line_ids = fields.One2many(
        "po.invoice.link.line",
        "wizard_id",
        string="Po_line to invoice_line link",
        default=lambda self: self._default_link_line_ids(),
    )

    def _default_link_line_ids(self):
        po_id = self.env["purchase.order"].browse(
            self.env.context.get("active_ids", [])
        )

        return [
            (0, 0, {"po_line_id": line.id})
            for line in po_id.order_line
            if not line.invoice_lines
        ]

    @api.onchange("po_id")
    def _compute_invoice_domain(self):
        if self.po_id.partner_id.commercial_partner_id.id is not False:
            pid = self.po_id.partner_id.commercial_partner_id.id
            search_for = "partner_id.commercial_partner_id"
        else:
            pid = self.po_id.partner_id.id
            search_for = "partner_id"
        return {
            "domain": {
                "invoice_id": [
                    (
                        search_for,
                        "=",
                        pid,
                    ),
                    (
                        "type",
                        "=",
                        "in_invoice",
                    ),
                ]
            }
        }

    def action_assign_invoice(self):
        for link in self.link_line_ids:
            link.invoice_line_id.name = "%s: %s" % (
                link.wizard_id.po_id.name,
                link.invoice_line_id.name,
            )
            link.po_line_id.invoice_lines |= link.invoice_line_id
        self.link_line_ids.mapped("invoice_line_id.invoice_id").update(
            {"origin": link.wizard_id.po_id.name}
        )

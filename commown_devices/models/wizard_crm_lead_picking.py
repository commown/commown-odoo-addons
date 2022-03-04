from odoo import models, fields, api


class CrmLeadPickingWizard(models.TransientModel):
    _name = "crm.lead.picking.wizard"
    _description = "Create a picking from a lead"

    lead_id = fields.Many2one(
        "crm.lead",
        string="Lead",
        required=True,
    )

    date = fields.Datetime(
        string="Date",
        help="Defaults to now - To be set only to force a date",
    )

    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Product",
        domain="[('tracking', '=', 'serial')]",
        required=True,
        default=lambda self: self._compute_default_product_tmpl_id(),
    )

    variant_id = fields.Many2one(
        "product.product",
        string="Variant",
        domain=("[('tracking', '=', 'serial'),"
                " ('product_tmpl_id', '=', product_tmpl_id)]"),
        required=True,
    )

    lot_id = fields.Many2one(
        "stock.production.lot",
        string="Device",
        domain=lambda self: '''[
            ("product_id", "=", variant_id),
            ("quant_ids.location_id", "child_of", %d)]''' % self.env.ref(
                "commown_devices.stock_location_available_for_rent").id,
        required=True,
    )

    def _compute_default_product_tmpl_id(self):
        if not self.lead_id and "default_lead_id" in self.env.context:
            lead = self.env["crm.lead"].browse(
                self.env.context["default_lead_id"])
        else:
            lead = self.lead_id
        possible_products = lead.contract_id.mapped(
            "contract_line_ids.sale_order_line_id"
            ".product_id.product_tmpl_id.storable_product_id")
        return possible_products and possible_products[0]

    @api.onchange("product_tmpl_id")
    def onchange_product_tmpl_id(self):
        if self.product_tmpl_id:
            if len(self.product_tmpl_id.product_variant_ids) == 1:
                self.variant_id = self.product_tmpl_id.product_variant_id
            else:
                self.variant_id = False

    @api.multi
    def create_picking(self):
        quant = self.lot_id.quant_ids.filtered(
            lambda q: q.quantity > 0).ensure_one()
        return self.lead_id.contract_id.send_device(quant, date=self.date)

from odoo import _, api, fields, models

from .common import find_products_orig_location


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

    all_products = fields.Many2many(
        "product.product",
        string="All product to send",
        required=True,
        domain=[("type", "=", "product")],
        default=lambda self: self._compute_default_product_ids(),
    )

    lot_ids = fields.Many2many(
        "stock.production.lot",
        string="Tracked Devices",
        required=True,
    )

    prioritize_repackaged = fields.Boolean(
        "Send from repackaged devices if possible",
        default=True,
    )

    products_locations = fields.Text(
        "Products will be sent from",
        default=lambda self: self._compute_products_locations(),
    )

    @api.multi
    @api.onchange("all_products", "lot_ids")
    def _compute_lot_domain(self):
        """The lots domain are products from all_products that
        are tracked by serial number (tracking = 'serial')
        and with no lot already selected in lot_ids
        """
        avail_loc = self.env.ref("commown_devices.stock_location_available_for_rent")
        for rec in self:
            picked_product_ids = rec.lot_ids.mapped("product_id").ids
            ids_to_include = rec.all_products.filtered(
                lambda p: p.tracking == "serial" and p.id not in picked_product_ids
            ).ids
            quant_domain = [
                ("location_id", "child_of", avail_loc.id),
                ("product_id.id", "in", ids_to_include),
            ]
            quants = (
                self.env["stock.quant"]
                .search(quant_domain)
                .filtered(lambda q: q.quantity > q.reserved_quantity)
            )
            return {"domain": {"lot_ids": [("id", "in", quants.mapped("lot_id").ids)]}}

    def _compute_untracked_products(self):
        return self.all_products.filtered(lambda p: p.tracking == "none")

    def _compute_send_from(self):
        loc_new = self.env.ref("commown_devices.stock_location_modules_and_accessories")
        loc_repackaged = self.env.ref(
            "commown_devices.stock_repackaged_modules_and_accessories"
        )

        if self.prioritize_repackaged:
            send_nonserial_products_from = loc_repackaged + loc_new
        else:
            send_nonserial_products_from = loc_new + loc_repackaged
        return send_nonserial_products_from

    def _compute_products_locations(self):
        return find_products_orig_location(
            self.env,
            {pt: 1 for pt in self._compute_untracked_products()},
            self._compute_send_from(),
            compute_summary=True,
        )["text_summary"]

    @api.onchange("all_products", "prioritize_repackaged")
    def onchange_all_products_or_priority(self):
        self.products_locations = self._compute_products_locations()

    def _compute_default_product_ids(self):
        if not self.lead_id and "default_lead_id" in self.env.context:
            lead = self.env["crm.lead"].browse(self.env.context["default_lead_id"])
        else:
            lead = self.lead_id
        services = lead.contract_id.mapped(
            "contract_line_ids.sale_order_line_id.product_id"
        )
        default_products = services.mapped("primary_storable_variant_id")
        default_products |= services.mapped("secondary_storable_variant_ids")
        return default_products

    @api.multi
    def create_picking(self):
        nb_of_tracked_product = len(
            self.all_products.filtered(lambda p: p.tracking == "serial")
        )
        assert len(self.lot_ids) == nb_of_tracked_product, _(
            "You have to select a lot for each tracked product"
        )
        products = {u: 1 for u in self._compute_untracked_products()}
        return self.lead_id.contract_id.send_devices(
            self.lot_ids,
            products,
            send_nonserial_products_from=self._compute_send_from(),
            date=self.date,
        )

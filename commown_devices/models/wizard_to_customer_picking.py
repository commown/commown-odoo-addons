from odoo import _, api, fields, models

from .common import find_products_orig_location


class PickingToCustomerWizard(models.AbstractModel):
    _name = "abstract.to.customer.wizard"
    _description = "Abstract class for wizards to send a device after a rental or order"

    # To be overriden:
    entity_id = fields.Many2one("crm.lead", string="Lead", required=True)

    usage = fields.Selection(related="entity_id.contract_id.stock_ownership")

    date = fields.Datetime(
        string="Date",
        help="Defaults to now - To be set only to force a date",
    )

    all_products = fields.Many2many(
        "product.product",
        string="All products to send",
        required=True,
        domain=[("product_tmpl_id.type", "=", "product")],
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

    def _get_related_entity(self, allow_use_default=True):
        entity = self.entity_id
        model_name = self._fields["entity_id"].comodel_name
        if allow_use_default and not entity and "default_entity_id" in self.env.context:
            entity = self.env[model_name].browse(self.env.context["default_entity_id"])
        return entity

    @api.multi
    @api.onchange("all_products", "lot_ids")
    def _compute_lot_domain(self):
        """The lots domain are products from all_products that
        are tracked by serial number (tracking = 'serial')
        and with no lot already selected in lot_ids
        """
        for rec in self:
            contract = self._get_related_entity(allow_use_default=True).contract_id
            avail_loc = contract.send_default_location()
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

    def _compute_send_non_serial_from(self):
        """Return the (ordered) non serial products' origin possible locations

        The result depends on the contract's ownership and the priorization of repackage
        modules/ accessories usage (when in rental use case only).
        """
        ref = self.env.ref

        if self.usage == "internal":
            loc_new = ref("commown_devices.stock_location_modules_and_accessories")
            loc_repack = ref("commown_devices.stock_repackaged_modules_and_accessories")
            if self.prioritize_repackaged:
                return loc_repack + loc_new
            else:
                return loc_new + loc_repack
        else:
            return ref("stock.stock_location_stock")

    def _compute_products_locations(self):
        return find_products_orig_location(
            self.env,
            {pt: 1 for pt in self._compute_untracked_products()},
            self._compute_send_non_serial_from(),
            compute_summary=True,
        )["text_summary"]

    @api.onchange("all_products", "prioritize_repackaged")
    def onchange_all_products_or_priority(self):
        self.products_locations = self._compute_products_locations()

    def _compute_default_product_ids(self):
        services = self._get_related_entity(allow_use_default=True).mapped(
            "contract_id.contract_line_ids.sale_order_line_id.product_id"
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
        return self._get_related_entity().contract_id.send_devices(
            self.lot_ids,
            products,
            send_nonserial_products_from=self._compute_send_non_serial_from(),
            date=self.date,
        )


class CrmLeadPickingToCustomerWizard(models.TransientModel):
    _name = "crm.lead.to.customer.wizard"
    _inherit = "abstract.to.customer.wizard"
    _description = "Create a picking from a lead right after a rental sale"

    entity_id = fields.Many2one("crm.lead", string="Lead", required=True)


class ProjectTaskPickingToCustomerWizard(models.TransientModel):
    _name = "project.task.to.customer.wizard"
    _inherit = "abstract.to.customer.wizard"
    _description = "Create a picking from a task right after a sale with services order"

    entity_id = fields.Many2one("project.task", string="Task", required=True)

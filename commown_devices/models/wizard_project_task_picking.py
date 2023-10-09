from odoo import _, api, fields, models
from odoo.exceptions import UserError, Warning

from .common import find_products_orig_location, internal_picking

RESILIATION_XML_ID = "product_rental.contract_termination_project"


class ProjectTaskAbstractPickingWizard(models.AbstractModel):
    _name = "project.task.abstract.picking.wizard"
    _description = "Abstract model to create a picking from a task"

    task_id = fields.Many2one(
        "project.task",
        string="Task",
        required=True,
    )

    date = fields.Datetime(
        string="Date",
        help="Defaults to now - To be set only to force a date",
    )


class ProjectTaskInvolvedDevicePickingWizard(models.TransientModel):
    _name = "project.task.involved_device_picking.wizard"
    _inherit = "project.task.abstract.picking.wizard"
    _description = "Create a picking of the device attached to a task"

    destination_refs = (
        "stock_location_outsourced_repair",
        "stock_location_repackaged_devices",
        "stock_location_devices_to_check",
        "stock_location_repairer",
    )

    location_dest_id = fields.Many2one(
        "stock.location",
        string="Destination",
        required=True,
    )

    present_location_id = fields.Many2one(
        "stock.location",
        string="Present location of the product",
        required=True,
    )

    def _possible_dest_locations(self):
        """Possible destinations: all listed the `destination_ref` attribute
        and their children, excluding views.
        """
        orig_location = self.present_location_id
        result = self.env["stock.location"]

        for ref in self.destination_refs:
            loc = self.env.ref("commown_devices.%s" % ref)

            if loc != orig_location:
                if loc.usage == "view":
                    result |= result.search(
                        [
                            ("id", "child_of", loc.id),
                            ("usage", "!=", "view"),
                            ("id", "!=", orig_location.id),
                        ]
                    )
                else:
                    result |= loc

        return result

    def _set_present_location(self):
        self.present_location_id = self.task_id.lot_id.quant_ids.filtered(
            lambda q: q.quantity > 0
        ).location_id

    @api.onchange("task_id")
    def onchange_task_id(self):
        if self.task_id:
            self._set_present_location()
            dest_locations = self._possible_dest_locations()
            return {"domain": {"location_dest_id": [("id", "in", dest_locations.ids)]}}

    @api.multi
    def create_picking(self):
        if self.env.ref(RESILIATION_XML_ID) == self.task_id.project_id:
            raise Warning(_("This action should not be used in resiliation project"))

        lot = self.task_id.lot_id

        if not lot:
            raise UserError(_("Can't move device: no device set on this task!"))

        return internal_picking(
            [lot],
            {},
            self.env[
                "stock.location"
            ],  # No nonserial products are sent so location doesn't matter
            self.present_location_id,
            self.location_dest_id,
            self.task_id.get_name_for_origin(),
            date=self.date,
            do_transfer=True,
        )


class ProjectTaskInvolvedNonserialProductPickingWizard(models.TransientModel):
    _name = "project.task.involved_nonserial_product_picking.wizard"
    _inherit = "project.task.involved_device_picking.wizard"
    _description = "Create a picking of the nonserial product attached to a task"

    destination_refs = (
        "stock_location_outsourced_repair",
        "stock_repackaged_modules_and_accessories",
        "stock_location_devices_to_check",
        "stock_location_repairer",
    )

    def _set_present_location(self):
        self.present_location_id = self.env.ref(
            "commown_devices.stock_location_devices_to_check"
        ).id

    @api.multi
    def create_picking(self):
        if self.env.ref(RESILIATION_XML_ID) == self.task_id.project_id:
            raise Warning(_("This action should not be used in resiliation project"))

        return internal_picking(
            [],
            {self.task_id.storable_product_id: 1},
            self.present_location_id,
            self.env["stock.location"],  # No lot are sent so location doesn't matter
            self.location_dest_id,
            self.task_id.get_name_for_origin(),
            date=self.date,
            do_transfer=True,
        )


class ProjectTaskOutwardPickingWizard(models.TransientModel):
    _name = "project.task.outward.picking.wizard"
    _inherit = "project.task.abstract.picking.wizard"

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
        domain=(
            "[('tracking', '=', 'serial'),"
            " ('product_tmpl_id', '=', product_tmpl_id)]"
        ),
        required=True,
        default=lambda self: self._compute_default_variant_id(),
    )

    lot_id = fields.Many2one(
        "stock.production.lot",
        string="Device",
        domain=lambda self: self._domain_lot_id(),
        required=True,
    )

    def _get_task(self):
        if not self.task_id and "default_task_id" in self.env.context:
            return self.env["project.task"].browse(self.env.context["default_task_id"])
        else:
            return self.task

    def _compute_default_product_tmpl_id(self):
        return self._get_task().lot_id.product_id.product_tmpl_id

    def _compute_default_variant_id(self):
        return self._get_task().lot_id.product_id

    def _domain_lot_id(self):
        quant_domain = [
            (
                "location_id",
                "child_of",
                self.env.ref("commown_devices.stock_location_available_for_rent").id,
            ),
        ]
        if self.product_tmpl_id:
            quant_domain.append(("product_tmpl_id", "=", self.product_tmpl_id.id))
        if self.variant_id:
            quant_domain.append(("product_id", "=", self.variant_id.id))
        quants = (
            self.env["stock.quant"]
            .search(quant_domain)
            .filtered(lambda q: q.quantity > q.reserved_quantity)
        )
        return [("id", "in", quants.mapped("lot_id").ids)]

    @api.onchange("product_tmpl_id")
    def onchange_product_tmpl_id(self):
        domain = {}
        if self.product_tmpl_id:
            variants = self.product_tmpl_id.product_variant_ids
            if variants:
                domain["variant_id"] = [("id", "in", variants.ids)]
            if len(variants) == 1:
                self.variant_id = self.product_tmpl_id.product_variant_id
            elif self.variant_id not in variants:
                self.variant_id = False

        lots = self.env["stock.production.lot"].search(self._domain_lot_id())
        domain["lot_id"] = [("id", "in", lots.ids)]
        return {"domain": domain}

    @api.onchange("variant_id")
    def onchange_variant_id(self):
        if self.variant_id and self.product_tmpl_id != self.variant_id.product_tmpl_id:
            self.product_tmpl_id = self.variant_id.product_tmpl_id

        lots = self.env["stock.production.lot"].search(self._domain_lot_id())
        return {"domain": {"lot_id": [("id", "in", lots.ids)]}}

    @api.onchange("lot_id")
    def onchange_lot_id(self):
        if self.lot_id:
            self.variant_id = self.lot_id.product_id

    @api.multi
    def create_picking(self):
        send_lots_from = self.env.ref(
            "commown_devices.stock_location_available_for_rent"
        )
        return self.task_id.contract_id.send_devices(
            [self.lot_id],
            {},
            send_lots_from=send_lots_from,
            origin=self.task_id.get_name_for_origin(),
            date=self.date,
        )


class ProjectTaskInwardPickingWizard(models.TransientModel):
    _name = "project.task.inward.picking.wizard"
    _inherit = "project.task.abstract.picking.wizard"

    lot_id = fields.Many2one(
        "stock.production.lot",
        string="Device",
        required=True,
    )

    @api.onchange("task_id")
    def onchange_task_id(self):
        if self.task_id:
            lots = self.task_id.contract_id.lot_ids
            if len(lots) == 1:
                self.lot_id = lots.id
            return {"domain": {"lot_id": [("id", "in", lots.ids)]}}

    @api.multi
    def create_picking(self):
        return self.task_id.contract_id.receive_devices(
            [self.lot_id],
            {},
            self.env.ref("commown_devices.stock_location_devices_to_check"),
            origin=self.task_id.get_name_for_origin(),
            date=self.date,
        )


class ProjectTaskContractTransferWizard(models.TransientModel):
    _name = "project.task.contract_transfer.wizard"
    _inherit = "project.task.abstract.picking.wizard"

    contract_id = fields.Many2one(
        "contract.contract",
        string="Destination contract",
        required=True,
        domain=[("date_end", "=", False)],
    )

    @api.multi
    def create_transfer(self):
        lot = self.task_id.lot_id

        if not lot:
            raise UserError(_("Can't move device: no device set on this task!"))

        transfer_location = self.env.ref(
            "commown_devices.stock_location_contract_transfer"
        )

        self.task_id.contract_id.receive_devices(
            [self.task_id.lot_id],
            {},
            transfer_location,
            date=self.date,
            do_transfer=True,
        )

        self.contract_id.send_devices(
            [self.task_id.lot_id],
            {},
            send_lots_from=transfer_location,
            date=self.date,
            do_transfer=True,
        )


class ProjectTaskNoTrackingOutwardPickingWizard(models.TransientModel):
    _name = "project.task.notracking.outward.picking.wizard"
    _inherit = "project.task.abstract.picking.wizard"

    variant_id = fields.Many2one(
        "product.product",
        string="Product",
        domain="[('tracking', '=', 'none'), ('type', '=', 'product')]",
        required=True,
    )

    prioritize_repackaged = fields.Boolean(
        "Send from repackaged devices if possible",
        default=True,
    )

    product_location = fields.Text(
        "Product will be sent from",
        default=lambda self: self._compute_product_location(),
    )

    def _compute_product_location(self):
        if self.variant_id:
            loc = find_products_orig_location(
                self.env,
                {self.variant_id: 1},
                self._compute_send_from(),
                compute_summary=True,
            )["text_summary"]
        else:
            loc = ""
        return loc

    @api.onchange("variant_id", "prioritize_repackaged")
    def onchange_variant_id_or_priority(self):
        self.product_location = self._compute_product_location()

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

    @api.multi
    def create_picking(self):
        return self.task_id.contract_id.send_devices(
            [],  # Lots
            {self.variant_id: 1},
            send_nonserial_products_from=self._compute_send_from(),
            origin=self.task_id.get_name_for_origin(),
            date=self.date,
            do_transfer=False,
        )


class ProjectTaskNoTrackingInwardPickingWizard(models.TransientModel):
    _name = "project.task.notracking.inward.picking.wizard"
    _inherit = "project.task.abstract.picking.wizard"

    variant_id = fields.Many2one(
        "product.product",
        string="Product",
        domain="[('tracking', '=', 'none'), ('type', '=', 'product')]",
        required=True,
    )

    @api.multi
    def create_picking(self):
        return self.task_id.contract_id.receive_devices(
            [],
            {self.variant_id: 1},
            self.env.ref("commown_devices.stock_location_devices_to_check"),
            origin=self.task_id.get_name_for_origin(),
            date=self.date,
            do_transfer=False,
        )

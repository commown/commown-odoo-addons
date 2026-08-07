import json
from datetime import datetime, timedelta, timezone

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PickingOrderWizard(models.TransientModel):
    _name = "commown_devices.picking_order_wizard"
    _description = "Generic picking order wizard"

    document_model = fields.Char("Document model", readonly=True)
    document_id = fields.Integer("Document ID", readonly=True)

    usage = fields.Char(
        compute="_compute_document_dependant",
        readonly=True,
    )

    scheduled_date = fields.Datetime(
        string="Scheduled date",
        default="_compute_default_scheduled_date",
        required=True,
    )

    products = fields.Many2many(
        "product.product",
        string="Products to send",
        required=True,
        domain=[("product_tmpl_id.type", "=", "product")],
        default="_compute_default_product_ids",
    )

    carrier_account = fields.Many2one(
        "carrier.account",
        string="Carrier account",
        compute="_compute_document_dependant",
        readonly=True,
    )

    comment = fields.Text(help="You can add a comment for the preparation team here")

    os_required = fields.Boolean()

    os = fields.Selection(
        [
            ("none", "No OS"),
            ("android", "Android standard"),
            ("eos", "e/OS/"),
            ("windows", "Windows"),
            ("ubuntu", "Ubuntu"),
        ],
        string="Operating system",
    )

    is_return = fields.Boolean()

    orig_location = fields.Many2one(
        "stock.location",
        string="Origin location",
        readonly=True,
        compute="_compute_document_dependant",
    )

    dest_location = fields.Many2one(
        "stock.location",
        string="Destination location",
        readonly=True,
        compute="_compute_document_dependant",
    )

    def _document(self):
        if self.document_model and self.document_id:
            return self.env[self.document_model].browse(self.document_id).exists()
        else:
            raise UserError(_("Could not determine picking wizard origin document!"))

    def _compute_default_scheduled_date(self):
        doc_parent = self._document()._shipping_parent()

        scheduled_date = fields.Datetime.context_timestamp(
            self.env.user, datetime.now()
        )

        if doc_parent.picking_scheduled_in_days:
            scheduled_date += timedelta(days=doc_parent.picking_scheduled_in_days)

        if doc_parent.picking_scheduled_forced_hour > 0:
            scheduled_date = scheduled_date.replace(
                hour=doc_parent.picking_scheduled_forced_hour,
                minute=0,
                second=0,
                microsecond=0,
            )

        return scheduled_date.astimezone(timezone.utc).replace(tzinfo=None)

    def _compute_default_product_ids(self):
        doc = self._document()
        if doc.contract_id:
            services = doc.contract_id.mapped(
                "contract_line_ids.sale_order_line_id.product_id"
            )
            default_products = services.mapped("primary_storable_variant_id")
            default_products |= services.mapped("secondary_storable_variant_ids")
            return default_products
        elif doc.product_id:
            return doc.product_id

    @api.depends("document_model", "document_id")
    def _compute_document_dependant(self):
        doc = self._document()
        doc_parent = doc._shipping_parent()

        self.usage = doc.contract_id.stock_ownership
        self.carrier_account = doc_parent.carrier_account_id
        self.os_required = doc_parent.picking_os_required

        self._compute_orig_location(doc, doc_parent)
        self._compute_dest_location(doc, doc_parent)

    def _compute_orig_location(self, doc, doc_parent):
        "Set the origin location of current wizard instance"

        if not self.is_return:
            if doc_parent.orig_from_contract_usage:
                if not doc.contract_id:
                    raise UserError(
                        _("A contract is required to compute the origin location")
                    )
                self.orig_location = doc.contract_id.send_default_location()
            else:
                if not doc_parent.picking_orig:
                    raise UserError(_("Could not determine origin location"))
                self.orig_location = doc_parent.picking_orig

        else:  # return case
            if not doc_parent.picking_dest_contract_partner:
                raise UserError(_("Could not determine origin location (return)"))
            contract = doc.contract_id
            self.orig_location = contract.partner_id.get_or_create_customer_location(
                contract.stock_ownership
            )

    def _compute_dest_location(self, doc, doc_parent):
        "Set the destination location onf current wizard instance"

        if not self.is_return:
            if doc_parent.picking_dest_contract_partner:
                contract = doc.contract_id
                if not contract:
                    raise UserError(
                        _("A contract is required to compute the destination location")
                    )
                self.dest_location = (
                    contract.partner_id.get_or_create_customer_location(self.usage)
                )
            else:
                if not doc_parent.picking_dest:
                    raise UserError(_("Could not determine destination location"))

        else:  # return case
            if doc_parent.picking_return_to:
                self.dest_location = doc_parent.picking_return_to
            else:
                raise UserError(_("Could not determine destination location (return)"))

    def create_picking(self):
        doc = self._document()
        doc_parent = doc._shipping_parent()
        contract = doc.contract_id  # may be False!

        orig_loc, dest_loc = None, None

        if self.is_return:
            if not contract:
                raise UserError(_("Return is only allowed with a contract!"))
            orig_loc = contract.send_default_location()

        elif doc_parent.picking_to_contract_partner_location:
            if not contract:
                raise UserError(
                    _(
                        "No contract set but %(name)s %(doc_model)s (ID=%(doc_id)s)"
                        " requires a picking to contract's partner!"
                    )
                    % {
                        "name": doc_parent.name,
                        "doc_model": self.document_model,
                        "id": doc_parent.id,
                    }
                )
            dest_loc = contract.send_default_location()

        if orig_loc is None and len(self.possible_orig_locations) == 1:
            orig_loc = self.possible_orig_locations

        if not orig_loc:
            raise UserError(_("Unable to determine origin location"))

        if dest_loc is None:
            dest_loc = self.dest_location

        if not dest_loc:
            raise UserError(_("Unable to determine destination location"))

        attrs = {
            "partner_id": contract and contract.partner_id.id,
            "move_type": "direct",
            "picking_type_id": doc_parent.picking_type_id.id,
            "location_id": orig_loc.id,
            "location_dest_id": self.dest_location.id,
            "scheduled_date": self.scheduled_date,
            "origin_document_id": self.document_id,
            "origin_document_model": self.document_model,
            "note": self.comment,
        }

        if self.carrier_account:
            attrs["carrier_domain"] = json.dumps(
                [("carrier_account_id", "=", self.carrier_account.id)]
            )

        picking = self.env["stock.picking"].create(attrs)

        for product in self.products:
            self.env["stock.move"].create(
                {
                    "name": product.name,
                    "picking_id": picking.id,
                    "picking_type_id": picking.picking_type_id.id,
                    "location_id": picking.location_id.id,
                    "location_dest_id": picking.location_dest_id.id,
                    "product_id": product.id,
                    "product_uom_qty": 1,
                    "product_uom": product.uom_id.id,
                    "date": picking.scheduled_date,
                }
            )

        picking.action_confirm()
        picking.action_assign()

        # We choose the devices with a serial ourselves, so remove the
        # automatically assigned lots to avoid errors (keeping
        # assigned non serial products):
        for mol in picking.move_line_ids:
            mol.lot_id = False

        contract.move_ids |= picking.move_ids

        # Link created picking to the initial sale
        if contract.stock_ownership == "customer":
            so = contract.mapped("contract_line_ids.sale_order_line_id.order_id")
            so.picking_ids |= picking
            # Also try to link moves and sale lines:
            so_lines = so.order_line
            for move in picking.move_ids:
                so_line = so_lines.filtered(lambda ol: ol.product_id == move.product_id)
                if so_line:
                    move.sale_line_id = so_line[0]

        return picking

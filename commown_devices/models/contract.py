import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .common import do_new_transfer, internal_picking

_logger = logging.getLogger(__name__)


class Contract(models.Model):
    _inherit = "contract.contract"

    move_line_ids = fields.One2many(
        "stock.move.line",
        string="Move Lines",
        compute="_compute_move_line_ids",
        store=False,
    )

    move_ids = fields.One2many(
        "stock.move",
        "contract_id",
        string="Stock Move",
    )

    lot_ids = fields.One2many("stock.lot", "contract_id", string="Lots")

    lot_nb = fields.Integer("Number of lots", compute="_compute_lot_nb", store=True)

    def pending_picking(self):
        "Return current contract pickings in the 'confirmed' or 'assigned' state"
        return self.move_ids.picking_id.filtered(
            lambda p: p.state in ("confirmed", "assigned")
        )

    @api.depends("move_ids.move_line_ids")
    def _compute_move_line_ids(self):
        for rec in self:
            rec.move_line_ids = rec.move_ids.mapped("move_line_ids")

    @api.depends("lot_ids")
    def _compute_lot_nb(self):
        for rec in self:
            rec.lot_nb = len(rec.lot_ids)

    def send_default_location(self):
        loc_ref = {
            "internal": "commown_devices.stock_location_available_for_rent",
            "customer": "stock.stock_location_stock",
        }
        return self.env.ref(loc_ref[self.stock_ownership])

    def ask_picking(
        self,
        origin,
        scheduled_date,
        products,
        carrier_account,
        comment,
        picking_type,
    ):
        dest_location = self.partner_id.get_or_create_customer_location(
            self.stock_ownership
        )
        picking = self.env["stock.picking"].create(
            {
                "partner_id": self.partner_id.id,
                "move_type": "direct",
                "picking_type_id": picking_type.id,
                "location_id": self.send_default_location().id,
                "location_dest_id": dest_location.id,
                "scheduled_date": scheduled_date,
                "origin_document_id": origin.id,
                "origin_document_model": origin._name,
                "note": comment,
            }
        )

        for product in products:
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

        self.move_ids |= picking.move_ids

        return picking

    def send_devices(
        self,
        lots,
        products,
        send_nonserial_products_from=None,
        send_lots_from=None,
        origin_document=None,
        date=None,
        do_transfer=False,
    ):
        """Create a picking of lot to partner's location.
        If given `date` is falsy (the default), it is set to now.
        If `do_transfer` is True (default: False), execute the picking
        at the previous date.
        """

        ungraded_lots = lots.filtered(lambda lot: not lot.grade_id)
        if ungraded_lots:
            raise UserError(
                _("Please set the grade on lots %(lots)s (ids: %(ids)s)")
                % {"lots": ungraded_lots.mapped("name"), "ids": ungraded_lots.ids}
            )

        dest_location = self.partner_id.get_or_create_customer_location(
            self.stock_ownership
        )
        default_stock = self.send_default_location()
        if send_nonserial_products_from is None:
            send_nonserial_products_from = default_stock
        if send_lots_from is None:
            send_lots_from = default_stock
        if origin_document is None:
            origin_document = self
        return self._create_picking(
            lots,
            products,
            send_nonserial_products_from,
            send_lots_from,
            dest_location,
            origin_document=origin_document,
            date=date,
            do_transfer=do_transfer,
        )

    def receive_devices(
        self,
        lots,
        products,
        dest_location,
        origin_document=None,
        date=False,
        do_transfer=False,
    ):
        """Create a picking from partner's location to `dest_location`.
        If given `date` is falsy (the default), it is set to now.
        If `do_transfer` is True (default: False), execute the picking
        at the previous date.
        """
        if origin_document is None:
            origin_document = self

        location = self.partner_id.get_or_create_customer_location(self.stock_ownership)

        return self._create_picking(
            lots,
            products,
            location,
            location,
            dest_location,
            origin_document=origin_document,
            date=date,
            do_transfer=do_transfer,
        )

    def _create_picking(
        self,
        lots,
        products,
        send_products_from,
        send_lots_from,
        dest_location,
        origin_document,
        date=None,
        do_transfer=False,
    ):
        self.ensure_one()
        new_moves = internal_picking(
            lots,
            products,
            send_products_from,
            send_lots_from,
            dest_location,
            origin_document,
            date=date,
        )
        self.move_ids |= new_moves
        if do_transfer:
            do_new_transfer(
                new_moves.mapped("picking_id"),
                date or fields.Datetime.now(),
            )
        return new_moves

    def _partner_location_changed(self, old_location=None):
        """Change all present contract stock-related entities customer-side location
        to the one

        Works by updating the pickings, moves and moves lines source or destination
        locations when they are equal to or child of given old location (or standard
        customer location if not passed).

        """
        self.ensure_one()
        if old_location is None:
            old_location = self.env.ref("stock.stock_location_customers")
        new_loc = self.partner_id.get_or_create_customer_location(self.stock_ownership)

        for picking in self.move_ids.mapped("picking_id"):
            for attr in ("location_id", "location_dest_id"):
                loc = getattr(picking, attr)

                if loc == old_location or loc.location_id == old_location:
                    setattr(picking, attr, new_loc.id)

                    picking.move_ids.update({attr: new_loc.id})
                    picking.move_line_ids.update({attr: new_loc.id})

                    # Reset picking, moves, move lines and quant dates
                    if picking.state == "done":
                        picking.action_set_date_done_to_scheduled()

                    break

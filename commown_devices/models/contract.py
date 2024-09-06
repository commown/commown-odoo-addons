import logging

from odoo import api, fields, models

from .common import _assigned, do_new_transfer, internal_picking

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

    lot_ids = fields.One2many("stock.production.lot", "contract_id", string="Lots")

    lot_nb = fields.Integer("Number of lots", compute="_compute_lot_nb", store=True)

    show_all_view_move_lines = fields.Boolean("Show all move lines", default=False)

    move_line_view_ids = fields.One2many(
        "stock.move.line",
        string="Move Lines",
        compute="_compute_move_line_view_ids",
        store=False,
    )

    def pending_picking(self):
        return self.move_ids.mapped("picking_id").filtered(_assigned)

    @api.depends("move_ids.move_line_ids")
    def _compute_move_line_ids(self):
        for rec in self:
            rec.move_line_ids = rec.move_ids.mapped("move_line_ids")

    @api.onchange("show_all_view_move_lines")
    def _compute_move_line_view_ids(self):
        if self.show_all_view_move_lines:
            move_ids = self.move_line_ids
        else:
            move_ids = self.move_line_ids.filtered("lot_id")

        self.update({"move_line_view_ids": [(6, 0, move_ids.ids)]})

    @api.depends("lot_ids")
    def _compute_lot_nb(self):
        for rec in self:
            rec.lot_nb = len(rec.lot_ids)

    @api.multi
    def send_devices(
        self,
        lots,
        products,
        send_nonserial_products_from=None,
        send_lots_from=None,
        origin=None,
        date=None,
        do_transfer=False,
    ):
        """Create a picking of lot to partner's location.
        If given `date` is falsy (the default), it is set to now.
        If `do_transfer` is True (default: False), execute the picking
        at the previous date.
        """
        dest_location = self.partner_id.get_or_create_customer_location()
        default_stock = self.env.ref(
            "commown_devices.stock_location_available_for_rent"
        )
        if send_nonserial_products_from is None:
            send_nonserial_products_from = default_stock
        if send_lots_from is None:
            send_lots_from = default_stock
        if origin is None:
            origin = self.name
        return self._create_picking(
            lots,
            products,
            send_nonserial_products_from,
            send_lots_from,
            dest_location,
            origin=origin,
            date=date,
            do_transfer=do_transfer,
        )

    @api.multi
    def receive_devices(
        self,
        lots,
        products,
        dest_location,
        origin=None,
        date=False,
        do_transfer=False,
    ):
        """Create a picking from partner's location to `dest_location`.
        If given `date` is falsy (the default), it is set to now.
        If `do_transfer` is True (default: False), execute the picking
        at the previous date.
        """
        if origin is None:
            origin = self.name

        location = self.partner_id.get_or_create_customer_location()

        return self._create_picking(
            lots,
            products,
            location,
            location,
            dest_location,
            origin=origin,
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
        origin,
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
            origin,
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
        new_loc = self.partner_id.get_or_create_customer_location()

        for picking in self.move_ids.mapped("picking_id"):
            for attr in ("location_id", "location_dest_id"):
                loc = getattr(picking, attr)

                if loc == old_location or loc.location_id == old_location:
                    setattr(picking, attr, new_loc.id)

                    picking.move_lines.update({attr: new_loc.id})
                    picking.move_line_ids.update({attr: new_loc.id})

                    # Reset picking, moves, move lines and quant dates
                    if picking.state == "done":
                        picking.action_set_date_done_to_scheduled()

                    break

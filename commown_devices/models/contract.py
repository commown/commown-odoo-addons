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


    def pending_picking(self):
        return self.move_ids.mapped("picking_id").filtered(_assigned)

    @api.depends("move_ids.move_line_ids")
    def _compute_move_line_ids(self):
        for rec in self:
            rec.move_line_ids = rec.move_ids.mapped("move_line_ids")

    @api.multi
    def send_devices(
        self,
        lots,
        products,
        send_nonserial_products_from=None,
        send_lots_from=None,
        origin=None,
        date=None,
        reuse_picking=None,
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
        return self._create_or_reuse_picking(
            lots,
            products,
            send_nonserial_products_from,
            send_lots_from,
            dest_location,
            origin=origin,
            date=date,
            reuse_picking=reuse_picking,
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
        reuse_picking=None,
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

        return self._create_or_reuse_picking(
            lots,
            products,
            location,
            location,
            dest_location,
            origin=origin,
            date=date,
            reuse_picking=reuse_picking,
            do_transfer=do_transfer,
        )

    def _create_or_reuse_picking(
        self,
        lots,
        products,
        send_products_from,
        send_lots_from,
        dest_location,
        origin,
        date=None,
        reuse_picking=None,
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
            picking=reuse_picking,
        )
        self.move_ids |= new_moves
        if do_transfer:
            do_new_transfer(
                new_moves.mapped("picking_id"),
                date or fields.Datetime.now(),
            )
        return new_moves

    @api.multi
    def stock_at_date(self, date=None):
        "Return the lots at partner's location at the given date"
        self.ensure_one()

        if date is None:
            date = fields.Datetime.now()

        move_lines = self.env["stock.move.line"].search(
            [
                ("picking_id.contract_id", "=", self.id),
                ("date", "<=", date),
                ("state", "=", "done"),
            ],
            order="date ASC",
        )

        lot_ids = OrderedDict()
        partner_loc = self.partner_id.get_or_create_customer_location()
        for m in move_lines:
            lot = m.lot_id
            lot_ids.setdefault(lot.id, 0)
            lot_ids[lot.id] += m.location_dest_id == partner_loc and 1 or -1

        return self.env["stock.production.lot"].browse(
            [l_id for (l_id, total) in list(lot_ids.items()) if total > 0]
        )

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

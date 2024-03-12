import logging

from odoo import api, fields, models

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

    lot_ids = fields.One2many("stock.production.lot", "contract_id", string="Lots")

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

        return self._create_or_reuse_picking(
            lots,
            products,
            self.partner_id.get_or_create_customer_location(),
            self.partner_id.get_or_create_customer_location(),
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
